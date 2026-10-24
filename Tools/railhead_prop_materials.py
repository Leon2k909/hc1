"""Railhead's props: the materials the props' own scripts add (Tools/railhead_props.py and its helpers).

    python Tools/railhead_prop_materials.py --out <root laid out as Assets>     (default: nothing; give a root)

Every paint here is a material of its own under materials/railhead/: brushed graphite cladding and stainless trim for
the kiosks and bins, the snack machine's satin graphite cabinet and its lit back panel, the timetable cases' brushed
aluminium, the drums' worn enamels, cones, galvanised steel, the cab's coupler casting and headlamps, and one small atlas
of plates (rw_prop_signs: the bins' pictograms, mast numbers, the high-voltage warning, the SOS plate, Zs 3 digits).

write( root ) draws them into root/materials/railhead (a stage folder, or Assets at integration). Nothing here ever
writes Assets by itself: railhead_map.py doesn't call it. PAINTS is registered with railhead_buffer.PAINTS (and so with
railhead_materials.paints()), with each paint's tile size in inches.
"""
import argparse
import io
import math
import time
from pathlib import Path

import numpy as np

ROOT = Path( __file__ ).resolve().parent.parent
RESOURCE = "materials/railhead"
DEFAULT_AO = "materials/default/default_ao.tga"

# paint -> tile size (inches a texture repeat covers on a world-projected face; 1.0 where UVs are explicit)
PAINTS = {
    "rw_kiosk_clad": 24.0,          # brushed graphite cladding panels
    "rw_kiosk_white": 48.0,         # the kiosk's white interior (satin)
    "rw_stainless": 24.0,           # brushed stainless: counter nosings, bins, rails
    "rw_alu_brushed": 24.0,         # silver anodised aluminium: timetable cases, door frames
    "rw_vend_cabinet": 48.0,        # the snack machine's satin graphite powder coat
    "rw_vend_backlight": 48.0,      # the white LED panel behind the snack machine's goods
    "rw_coupler_cast": 24.0,        # the automatic coupler's cast steel
    "rw_train_headlamp": 24.0,      # LED headlamp lenses, lit
    "rw_galvanised": 36.0,          # hot-dip galvanised steel
    "rw_cone_orange": 24.0,         # PVC traffic cone
    "rw_reflective": 24.0,          # white retro-reflective sheeting
    "rw_drum_blue": 36.0,           # 200 l steel drums' enamels, worn
    "rw_drum_red": 36.0,
    "rw_drum_grey": 36.0,
    "rw_mast_concrete": 48.0,       # cast foundation blocks: smoother and greyer than the platforms' concrete
    "rw_prop_signs": 1.0,           # the plates' atlas (explicit UVs)
    "rw_emu_roof": 96.0,            # the EMU's light grey roof, sooted along it from the wire and the pantograph
    "rw_kiosk_fascia": 48.0,        # the kiosk's backlit opal fascia: a white light box
    "rw_kiosk_ink": 1.0,            # the kiosk atlas's lettering and icons, printed dark on the fascia (explicit UVs)
    "rw_kiosk_backlit": 1.0,        # the kiosk atlas's posters, backlit in the end vitrines (explicit UVs)
    "rw_estate_lens_red": 24.0,     # the estate car's tail lamp lenses: red, the clear covers and the dark reflectors
    "rw_estate_lens_clear": 24.0,
    "rw_estate_lens_dark": 24.0,
    "rw_case_glass": 64.0,          # clear float glass in the timetable cases and vitrines
    "rw_taxi_sign": 24.0,           # the taxi sign's yellow light box, faintly lit
    "rw_emu_screen": 64.0,          # the EMU's windscreen and display glass: glossy black, so it mirrors the shed
    "rw_bogie_dust": 36.0,          # the bogies' painted steel under years of brake and ballast dust: grey-brown
    "rw_bogie_brake": 36.0,         # the lowest parts (axle boxes, wheel webs, springs): darker with brake dust
    "rw_tyre_bright": 24.0,         # the wheels' turned tyre faces and treads: bright machined steel
    "rw_damper_grey": 24.0,         # the dampers' light grey bodies
    "rw_kiosk_membrane": 48.0,      # the kiosk roof's grey PVC membrane
    "rw_vend_band": 1.0,            # the snack machine's backlit name band (explicit UVs on the props' sign atlas)
    "rw_ticket_band": 24.0,         # the ticket machine's dark RAL 7016 header band
}

# The plates' atlas: name -> ( x0, y0, x1, y1 ) px, origin top left, 1024 square.
SIGN_SIZE = 1024
SIGN_RECTS = {
    "bin_paper": ( 16, 16, 216, 216 ),
    "bin_pack": ( 232, 16, 432, 216 ),
    "bin_rest": ( 448, 16, 648, 216 ),
    "mast_plate": ( 664, 16, 1008, 222 ),       # 250 x 150 mm: "34-12"
    "mast_plate_b": ( 664, 238, 1008, 444 ),    # "34-14"
    "warn_bolt": ( 16, 232, 216, 432 ),         # the yellow lightning triangle
    "sos": ( 232, 232, 432, 432 ),
    "zs3_6": ( 448, 232, 548, 432 ),            # a Zs 3 speed indicator's digit, white on black (6 = 60 km/h)
    "zs3_4": ( 556, 232, 656, 432 ),
    "info_head": ( 16, 448, 216, 648 ),         # the help point's opal head: a blue "i"
    "trough_mark": ( 232, 448, 432, 512 ),      # a cable trough lid's stencil
    "rack_mark": ( 448, 448, 648, 512 ),
    "taxi": ( 664, 460, 1008, 563 ),            # the taxi roof sign's face: black TAXI on yellow
    "vend_band": ( 16, 680, 520, 783 ),         # the snack machine's backlit name band (a made-up vending firm)
}


def rect_uv( name ):
    """ ( u0, v0, u1, v1 ) of a plate in rw_prop_signs, v up from the picture's bottom. """
    x0, y0, x1, y1 = SIGN_RECTS[name]
    return ( x0 / SIGN_SIZE, 1.0 - y1 / SIGN_SIZE, x1 / SIGN_SIZE, 1.0 - y0 / SIGN_SIZE )


# ---------------------------------------------------------------------------------------------------------------------
# Writing

def _save( path, image ):
    data = io.BytesIO()
    image.save( data, format="PNG", optimize=True )
    path.parent.mkdir( parents=True, exist_ok=True )
    if path.exists() and path.read_bytes() == data.getvalue():
        return
    temp = path.with_name( path.name + ".writing" )
    temp.write_bytes( data.getvalue() )
    for attempt in range( 20 ):
        try:
            temp.replace( path )
            return
        except PermissionError:
            time.sleep( 0.25 * ( attempt + 1 ) )
    temp.replace( path )


def _write_text( path, text ):
    path.parent.mkdir( parents=True, exist_ok=True )
    path.write_text( text, encoding="utf-8" )


def _field( rng, shape, sigma ):
    from scipy import ndimage
    a = ndimage.gaussian_filter( rng.normal( size=shape ).astype( np.float32 ), sigma, mode="wrap" )
    return a / ( a.std() + 1e-6 )


def _normal( height, strength ):
    gy, gx = np.gradient( height )
    n = np.dstack( ( -gx * strength, gy * strength, np.ones( height.shape ) ) )
    n /= np.linalg.norm( n, axis=2, keepdims=True )
    return n * 0.5 + 0.5


def flat_vmat( colour, metalness, roughness, illum=0.0 ):
    """ A flat colour, flat normals, one roughness (as railhead_materials' PAINTED), self-lit if illum. """
    r, g, b = ( c / 255.0 for c in colour )
    lines = [ "// Tools/railhead_prop_materials.py", '"Layer0"', "{", '    shader "shaders/complex.shader"',
              '    F_SPECULAR "1"' ]
    if illum:
        lines += [ '    F_SELF_ILLUM "1"', '    TextureSelfIllumMask "[1.000000 1.000000 1.000000 0.000000]"',
                   f'    g_flSelfIllumBrightness "{illum:.2f}"', '    g_flSelfIllumAlbedoFactor "1.0"',
                   '    g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"' ]
    lines += [ '    g_flRoughnessScaleFactor "1"', f'    g_flMetalness "{metalness:.2f}"',
               '    TextureColor "materials/default/default_color.tga"',
               '    TextureNormal "materials/default/default_normal.tga"',
               f'    TextureRoughness "[{roughness:.6f} {roughness:.6f} {roughness:.6f} 0.000000]"',
               f'    TextureAmbientOcclusion "{DEFAULT_AO}"',
               f'    g_vColorTint "[{r:.6f} {g:.6f} {b:.6f} 1.000000]"', '    g_flModelTintAmount "1.0"', "}" ]
    return "\n".join( lines ) + "\n"


def textured_vmat( name, metalness, illum=0.0, alpha=False, metal_map=False ):
    lines = [ "// Tools/railhead_prop_materials.py", '"Layer0"', "{", '    shader "shaders/complex.shader"',
              '    F_SPECULAR "1"' ]
    if metal_map:
        lines += [ '    F_METALNESS_TEXTURE "1"', f'    TextureMetalness "{RESOURCE}/{name}_metal.png"' ]
    if alpha:
        lines += [ '    F_ALPHA_TEST "1"', '    g_flAlphaTestReference "0.5"', '    g_flAntiAliasedEdgeStrength "1"',
                   f'    TextureTranslucency "{RESOURCE}/{name}_trans.png"' ]
    if illum:
        lines += [ '    F_SELF_ILLUM "1"', f'    TextureSelfIllumMask "{RESOURCE}/{name}_illum.png"',
                   f'    g_flSelfIllumBrightness "{illum:.2f}"', '    g_flSelfIllumAlbedoFactor "1.0"',
                   '    g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"' ]
    lines += [ '    g_flRoughnessScaleFactor "1"', f'    g_flMetalness "{metalness:.2f}"',
               f'    TextureColor "{RESOURCE}/{name}_color.png"', f'    TextureNormal "{RESOURCE}/{name}_normal.png"',
               f'    TextureRoughness "{RESOURCE}/{name}_rough.png"', f'    TextureAmbientOcclusion "{DEFAULT_AO}"',
               '    g_vColorTint "[1 1 1 1]"', '    g_flModelTintAmount "1.0"', "}" ]
    return "\n".join( lines ) + "\n"


def _write_maps( out, name, colour, rough, height, strength=1.0, metal=None ):
    from PIL import Image
    _save( out / f"{name}_color.png", Image.fromarray( np.clip( np.rint( colour ), 0, 255 ).astype( np.uint8 ), "RGB" ) )
    _save( out / f"{name}_rough.png", Image.fromarray( np.clip( np.rint( rough * 255 ), 0, 255 ).astype( np.uint8 ), "L" ) )
    _save( out / f"{name}_normal.png",
           Image.fromarray( np.clip( np.rint( _normal( height, strength ) * 255 ), 0, 255 ).astype( np.uint8 ), "RGB" ) )
    if metal is not None:
        _save( out / f"{name}_metal.png", Image.fromarray( np.clip( np.rint( metal * 255 ), 0, 255 ).astype( np.uint8 ), "L" ) )


def brushed( rng, size, base, rough, streak=0.06, fleck=0.015 ):
    """ Brushed sheet: fine grain running along the picture's u (horizontal), slow tone drift, a few handling marks. """
    h = w = size
    from scipy import ndimage
    fine = rng.normal( size=( h, w ) ).astype( np.float32 )
    grain = ndimage.gaussian_filter( fine, ( 0.45, 18.0 ), mode="wrap" )
    grain /= grain.std() + 1e-6
    drift = _field( rng, ( h, w ), 60 )
    marks = np.clip( _field( rng, ( h, w ), 9 ) - 1.9, 0, None )
    value = 1.0 + 0.5 * streak * grain + 0.02 * drift - 0.04 * marks + fleck * fine
    colour = np.asarray( base, float )[None, None, :] * value[..., None]
    r = np.clip( rough + 0.015 * grain + 0.06 * marks + 0.02 * drift, 0.05, 1.0 )
    height = 0.0006 * grain
    return colour, r, height


def worn_enamel( rng, size, base, rust=( 108, 62, 38 ), chips=0.012, streaks=True ):
    """ A drum's or a box's enamel after years in a yard: sun-faded, dusty, chipped to rust at its edges and hoops,
    with rust run down from the chips. v = 0 at the picture's bottom row. """
    from scipy import ndimage
    h = w = size
    broad, mid, fine = _field( rng, ( h, w ), 40 ), _field( rng, ( h, w ), 6 ), _field( rng, ( h, w ), 0.8 )
    colour = np.asarray( base, float )[None, None, :] * ( 1.0 + 0.06 * broad + 0.02 * fine )[..., None]
    chip = np.clip( ( _field( rng, ( h, w ), 1.6 ) + 0.6 * mid - 2.7 ) * 3.0, 0, 1 )
    chip = np.maximum( chip, ( rng.random( ( h, w ) ) < chips * 0.02 ).astype( float ) )
    chip = np.clip( ndimage.gaussian_filter( chip, 0.6, mode="wrap" ) * 1.6, 0, 1 )
    run = chip.copy()
    if streaks:
        for k in range( 1, 40 ):                                      # rust carried down by the rain
            run = np.maximum( run, np.roll( chip, k, axis=0 ) * ( 1.0 - k / 40.0 ) * 0.35 )
    rustc = np.asarray( rust, float )[None, None, :] * ( 1.0 + 0.15 * fine )[..., None]
    colour = colour * ( 1 - 0.45 * run[..., None] ) + rustc * 0.45 * run[..., None]
    colour = colour * ( 1 - chip[..., None] ) + rustc * chip[..., None]
    dust = np.clip( 0.05 + 0.04 * broad, 0, 0.14 )
    colour = colour * ( 1 - dust[..., None] ) + np.array( ( 150, 140, 124 ) ) * dust[..., None]
    rough = np.clip( 0.5 + 0.05 * mid + 0.35 * chip + 0.1 * dust, 0.25, 0.95 )
    height = 0.003 * fine - 0.02 * chip
    return colour, rough, height


def _font( size, bold=True ):
    from PIL import ImageFont
    return ImageFont.truetype( str( ROOT / "Assets/fonts" / ( "Dinish-Bold.ttf" if bold else "Dinish-Regular.ttf" ) ), size )


def _signs( out ):
    """ The plates' atlas. Each plate is drawn with a thin bright border and a few scuffs, the way enamel and vinyl
    plates look after a few winters. """
    from PIL import Image, ImageDraw
    S = SIGN_SIZE
    img = Image.new( "RGB", ( S, S ), ( 120, 120, 118 ) )
    rough = Image.new( "L", ( S, S ), 120 )
    d = ImageDraw.Draw( img )
    white, black = ( 238, 238, 232 ), ( 22, 23, 24 )

    def text( box, words, colour, size, bold=True ):
        x0, y0, x1, y1 = box
        while size > 8 and _font( size, bold ).getlength( words ) > ( x1 - x0 ) * 0.86:
            size -= 2
        d.text( ( ( x0 + x1 ) / 2, ( y0 + y1 ) / 2 ), words, font=_font( size, bold ), fill=colour, anchor="mm" )

    for name, colour, label in ( ( "bin_paper", ( 26, 82, 160 ), "Papier" ), ( "bin_pack", ( 236, 190, 30 ), "Verpackung" ),
                                 ( "bin_rest", ( 92, 96, 100 ), "Restabfall" ) ):
        x0, y0, x1, y1 = SIGN_RECTS[name]
        ink = black if name == "bin_pack" else white
        d.rounded_rectangle( ( x0, y0, x1 - 1, y1 - 1 ), 16, fill=colour )
        cx, cy = ( x0 + x1 ) / 2, y0 + 82
        if name == "bin_paper":            # a newspaper
            d.rectangle( ( cx - 42, cy - 34, cx + 42, cy + 34 ), outline=ink, width=7 )
            for k in range( 4 ):
                d.line( ( cx - 30, cy - 18 + 12 * k, cx + ( 6 if k == 0 else 30 ), cy - 18 + 12 * k ), fill=ink, width=5 )
        elif name == "bin_pack":           # a carton and a bottle
            d.rectangle( ( cx - 46, cy - 18, cx - 6, cy + 36 ), outline=ink, width=7 )
            d.polygon( ( ( cx - 46, cy - 18 ), ( cx - 26, cy - 36 ), ( cx - 6, cy - 18 ) ), outline=ink, width=6 )
            d.rounded_rectangle( ( cx + 10, cy - 14, cx + 40, cy + 36 ), 8, outline=ink, width=7 )
            d.rectangle( ( cx + 19, cy - 32, cx + 31, cy - 14 ), fill=ink )
        else:                              # a bag
            d.polygon( ( ( cx - 40, cy + 36 ), ( cx + 40, cy + 36 ), ( cx + 30, cy - 18 ), ( cx - 30, cy - 18 ) ),
                       outline=ink, width=7 )
            d.line( ( cx - 14, cy - 18, cx - 8, cy - 34, cx + 8, cy - 34, cx + 14, cy - 18 ), fill=ink, width=6 )
        text( ( x0 + 8, y0 + 140, x1 - 8, y1 - 10 ), label, ink, 44 )
    for name, number in ( ( "mast_plate", "34-12" ), ( "mast_plate_b", "34-14" ) ):
        x0, y0, x1, y1 = SIGN_RECTS[name]
        d.rectangle( ( x0, y0, x1 - 1, y1 - 1 ), fill=white, outline=black, width=6 )
        text( ( x0 + 10, y0 + 10, x1 - 10, y1 - 10 ), number, black, 150 )
    x0, y0, x1, y1 = SIGN_RECTS["warn_bolt"]
    d.rectangle( ( x0, y0, x1, y1 ), fill=( 120, 120, 118 ) )
    tri = ( ( ( x0 + x1 ) / 2, y0 + 8 ), ( x1 - 6, y1 - 12 ), ( x0 + 6, y1 - 12 ) )
    d.polygon( tri, fill=black )
    inner = ( ( ( x0 + x1 ) / 2, y0 + 30 ), ( x1 - 24, y1 - 24 ), ( x0 + 24, y1 - 24 ) )
    d.polygon( inner, fill=( 244, 200, 0 ) )
    cx = ( x0 + x1 ) / 2
    d.polygon( ( ( cx + 8, y0 + 62 ), ( cx - 22, y0 + 122 ), ( cx - 2, y0 + 122 ), ( cx - 12, y0 + 166 ),
                 ( cx + 24, y0 + 106 ), ( cx + 4, y0 + 106 ), ( cx + 16, y0 + 62 ) ), fill=black )
    x0, y0, x1, y1 = SIGN_RECTS["sos"]
    d.rounded_rectangle( ( x0, y0, x1 - 1, y1 - 1 ), 14, fill=( 196, 24, 28 ) )
    text( ( x0 + 8, y0 + 20, x1 - 8, y0 + 120 ), "SOS", white, 96 )
    text( ( x0 + 8, y0 + 120, x1 - 8, y1 - 16 ), "Notruf", white, 44, False )
    for name, digit in ( ( "zs3_6", "6" ), ( "zs3_4", "4" ) ):
        x0, y0, x1, y1 = SIGN_RECTS[name]
        d.rectangle( ( x0, y0, x1 - 1, y1 - 1 ), fill=( 14, 14, 15 ) )
        # a dot-matrix digit: lit LEDs on a 5 x 7 grid
        font = { "6": "..##.|.#...|#....|####.|#...#|#...#|.###.", "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#." }[digit]
        rows = font.split( "|" )
        pitch = ( x1 - x0 ) / 6.2
        for r, row in enumerate( rows ):
            for c, on in enumerate( row ):
                cx_, cy_ = x0 + pitch * ( c + 0.6 ), y0 + 30 + pitch * 1.18 * r
                d.ellipse( ( cx_ - 5, cy_ - 5, cx_ + 5, cy_ + 5 ), fill=( 236, 236, 228 ) if on == "#" else ( 30, 30, 32 ) )
    x0, y0, x1, y1 = SIGN_RECTS["info_head"]
    d.rectangle( ( x0, y0, x1 - 1, y1 - 1 ), fill=( 236, 238, 236 ) )
    d.ellipse( ( x0 + 30, y0 + 30, x1 - 30, y1 - 30 ), fill=( 20, 72, 150 ) )
    text( ( x0 + 30, y0 + 30, x1 - 30, y1 - 30 ), "i", white, 120 )
    for name, words in ( ( "trough_mark", "KABEL  50 Hz" ), ( "rack_mark", "FAHRRAD" ) ):
        x0, y0, x1, y1 = SIGN_RECTS[name]
        d.rectangle( ( x0, y0, x1 - 1, y1 - 1 ), fill=( 132, 132, 128 ) )
        text( ( x0 + 4, y0 + 4, x1 - 4, y1 - 4 ), words, ( 232, 230, 220 ), 40 )
    x0, y0, x1, y1 = SIGN_RECTS["taxi"]
    d.rectangle( ( x0, y0, x1 - 1, y1 - 1 ), fill=( 246, 204, 46 ) )
    text( ( x0 + 6, y0 + 6, x1 - 6, y1 - 6 ), "TAXI", black, 86 )
    x0, y0, x1, y1 = SIGN_RECTS["vend_band"]
    d.rectangle( ( x0, y0, x1 - 1, y1 - 1 ), fill=( 246, 247, 244 ) )
    d.rectangle( ( x0, y1 - 12, x1 - 1, y1 - 1 ), fill=( 226, 104, 24 ) )
    d.rounded_rectangle( ( x0 + 14, y0 + 12, x0 + 84, y1 - 22 ), 12, fill=( 18, 58, 120 ) )
    text( ( x0 + 14, y0 + 12, x0 + 84, y1 - 22 ), "P", white, 62 )
    text( ( x0 + 96, y0 + 4, x1 - 8, y0 + 60 ), "Pausenbox", ( 18, 46, 96 ), 58 )
    text( ( x0 + 96, y0 + 56, x1 - 8, y1 - 16 ), "Snacks · Getränke", ( 70, 76, 84 ), 28, False )
    # Scuffs: a few fine light scratches over every plate.
    rng = np.random.default_rng( 9811 )
    for _ in range( 260 ):
        x, y = rng.uniform( 0, S, 2 )
        length = rng.uniform( 4, 18 )
        a = rng.uniform( 0, math.pi )
        d.line( ( x, y, x + length * math.cos( a ), y + length * math.sin( a ) ), fill=( 205, 205, 200 ), width=1 )
    arr = np.asarray( img, np.float32 )
    rough_arr = np.full( ( S, S ), 0.38, np.float32 )
    from PIL import Image as _I
    _save( out / "rw_prop_signs_color.png", _I.fromarray( np.clip( arr, 0, 255 ).astype( np.uint8 ), "RGB" ) )
    _save( out / "rw_prop_signs_rough.png", _I.fromarray( np.uint8( rough_arr * 255 ), "L" ) )
    _save( out / "rw_prop_signs_normal.png", _I.new( "RGB", ( 64, 64 ), ( 128, 128, 255 ) ) )
    illum = np.zeros( ( S, S ), np.uint8 )
    x0, y0, x1, y1 = SIGN_RECTS["taxi"]
    illum[y0:y1, x0:x1] = 90
    for name in ( "zs3_6", "zs3_4", "info_head" ):
        x0, y0, x1, y1 = SIGN_RECTS[name]
        lum = arr[y0:y1, x0:x1].mean( axis=2 )
        illum[y0:y1, x0:x1] = np.where( lum > 150, 255, 0 ) if name != "info_head" else 200
    _save( out / "rw_prop_signs_illum.png", _I.fromarray( illum, "L" ) )
    _write_text( out / "rw_prop_signs.vmat", textured_vmat( "rw_prop_signs", 0.0, illum=1.2 ) )


def write( root ):
    """ Draws every paint into root/materials/railhead. """
    from PIL import Image
    out = Path( root ) / RESOURCE
    out.mkdir( parents=True, exist_ok=True )
    rng = np.random.default_rng( 70411 )
    # Brushed metals.
    for name, base, rough, metal, streak in ( ( "rw_kiosk_clad", ( 150, 154, 158 ), 0.5, 0.15, 0.025 ),
                                             ( "rw_stainless", ( 178, 180, 180 ), 0.30, 0.85, 0.05 ),
                                             ( "rw_alu_brushed", ( 190, 193, 195 ), 0.34, 0.75, 0.04 ) ):
        colour, r, height = brushed( rng, 512, base, rough, streak )
        _write_maps( out, name, colour, r, height, 2.0 )
        _write_text( out / f"{name}.vmat", textured_vmat( name, metal ) )
    # Galvanised steel: dull spangle, darker where it's weathered.
    from scipy import ndimage
    size = 512
    cells = ndimage.zoom( rng.random( ( 24, 24 ) ), size / 24, order=0 )
    colour = np.asarray( ( 150, 155, 157 ), float )[None, None, :] * ( 0.93 + 0.1 * cells + 0.03 * _field( rng, ( size, size ), 30 ) )[..., None]
    _write_maps( out, "rw_galvanised", colour, np.clip( 0.42 + 0.12 * cells, 0, 1 ), 0.002 * cells, 1.0 )
    _write_text( out / "rw_galvanised.vmat", textured_vmat( "rw_galvanised", 0.65 ) )
    # Worn enamels.
    for name, base in ( ( "rw_drum_blue", ( 30, 70, 132 ) ), ( "rw_drum_red", ( 150, 34, 28 ) ), ( "rw_drum_grey", ( 96, 100, 98 ) ) ):
        colour, r, height = worn_enamel( rng, 512, base )
        _write_maps( out, name, colour, r, height, 3.0 )
        _write_text( out / f"{name}.vmat", textured_vmat( name, 0.15 ) )
    # Cast foundations: fine-grained, with formwork joints and rain-darkened tops.
    fine, broad = _field( rng, ( size, size ), 0.9 ), _field( rng, ( size, size ), 26 )
    pores = ( rng.random( ( size, size ) ) < 0.004 ).astype( float )
    colour = np.asarray( ( 158, 156, 150 ), float )[None, None, :] * ( 1 + 0.03 * fine + 0.05 * broad - 0.25 * pores )[..., None]
    _write_maps( out, "rw_mast_concrete", colour, np.clip( 0.82 + 0.05 * fine, 0, 1 ), 0.01 * fine - 0.05 * pores, 2.0 )
    _write_text( out / "rw_mast_concrete.vmat", textured_vmat( "rw_mast_concrete", 0.0 ) )
    # Flat paints.
    for name, colour, metal, rough, illum in ( ( "rw_kiosk_white", ( 232, 231, 225 ), 0.0, 0.48, 0.0 ),
                                               ( "rw_vend_cabinet", ( 122, 126, 130 ), 0.35, 0.32, 0.0 ),
                                               ( "rw_vend_backlight", ( 236, 240, 244 ), 0.0, 0.4, 1.3 ),
                                               ( "rw_coupler_cast", ( 58, 60, 61 ), 0.55, 0.55, 0.0 ),
                                               ( "rw_train_headlamp", ( 252, 248, 238 ), 0.0, 0.1, 5.0 ),
                                               ( "rw_cone_orange", ( 226, 78, 24 ), 0.0, 0.48, 0.0 ),
                                               ( "rw_reflective", ( 234, 234, 228 ), 0.0, 0.22, 0.0 ),
                                               ( "rw_estate_lens_red", ( 150, 18, 16 ), 0.0, 0.12, 0.0 ),
                                               ( "rw_estate_lens_clear", ( 205, 208, 210 ), 0.2, 0.08, 0.0 ),
                                               ( "rw_estate_lens_dark", ( 40, 36, 36 ), 0.4, 0.15, 0.0 ),
                                               ( "rw_taxi_sign", ( 246, 206, 52 ), 0.0, 0.35, 0.5 ),
                                               ( "rw_emu_screen", ( 10, 12, 14 ), 0.0, 0.06, 0.0 ),
                                               ( "rw_bogie_dust", ( 98, 92, 86 ), 0.15, 0.72, 0.0 ),
                                               ( "rw_bogie_brake", ( 62, 55, 49 ), 0.2, 0.78, 0.0 ),
                                               ( "rw_tyre_bright", ( 172, 172, 170 ), 1.0, 0.25, 0.0 ),
                                               ( "rw_damper_grey", ( 150, 152, 150 ), 0.1, 0.5, 0.0 ),
                                               ( "rw_kiosk_membrane", ( 128, 130, 130 ), 0.0, 0.8, 0.0 ),
                                               ( "rw_ticket_band", ( 56, 62, 68 ), 0.25, 0.4, 0.0 ) ):
        _write_text( out / f"{name}.vmat", flat_vmat( colour, metal, rough, illum ) )
    # The EMU's roof: a light grey paint under a soot film from the wire, darker in streaks along the car and round
    # the pantograph's work, with rain marks across.
    size = 1024
    a, b = _field( rng, ( size, size ), ( 2.0, 60.0 ) ), _field( rng, ( size, size ), 18 )
    fine = _field( rng, ( size, size ), 0.8 )
    soot = np.clip( 0.12 + 0.07 * a + 0.05 * b, 0.03, 0.35 )
    colour = np.asarray( ( 176, 178, 176 ), float )[None, None, :] * ( 1 - soot[..., None] )         + np.asarray( ( 52, 48, 44 ), float )[None, None, :] * soot[..., None]
    colour *= ( 1 + 0.02 * fine )[..., None]
    _write_maps( out, "rw_emu_roof", colour, np.clip( 0.5 + 0.3 * soot + 0.03 * fine, 0, 1 ), 0.001 * fine, 1.0 )
    _write_text( out / "rw_emu_roof.vmat", textured_vmat( "rw_emu_roof", 0.05 ) )
    # The kiosk's light box and its dark print, and its backlit posters: the kiosk atlas's own pictures.
    _write_text( out / "rw_kiosk_fascia.vmat", flat_vmat( ( 244, 243, 236 ), 0.0, 0.35, 1.8 ) )
    _write_text( out / "rw_kiosk_ink.vmat", _atlas_vmat( "rw_kiosk", ( 0.07, 0.075, 0.08 ), alpha=True ) )
    _write_text( out / "rw_kiosk_backlit.vmat", _atlas_vmat( "rw_kiosk", ( 1.0, 1.0, 1.0 ), illum=0.9 ) )
    _write_text( out / "rw_case_glass.vmat", CASE_GLASS )
    _write_text( out / "rw_vend_band.vmat", _atlas_vmat( "rw_prop_signs", ( 1.0, 1.0, 1.0 ), illum=1.4 ) )
    _signs( out )
    write_round2( out )
    write_bench( out )
    print( f"wrote {len( PAINTS )} prop materials to {out}" )


# Round 2: the road vehicles' glazing, interiors, wheels and lamps; the EMU cab's interior, lamp field and grime;
# the Sh 2 board's enamel; the skip, the vending machine's body and the container's markings.
PAINTS2 = {
    "rw_car_glass": 64.0,           # laminated, lightly tinted car glass (glass.shader): ~35 % through
    "rw_emu_cab_glass": 64.0,       # the EMU windscreen's tinted glass: ~25 % through, the cab behind it
    "rw_lamp_lens": 24.0,           # clear polycarbonate lamp lenses (glass.shader)
    "rw_car_cloth": 24.0,           # dark seat cloth
    "rw_car_headlining": 48.0,      # the roof lining's light grey felt
    "rw_car_trim": 24.0,            # black-grey interior and exterior plastics
    "rw_car_chrome": 24.0,          # satin chrome strips and surrounds
    "rw_lamp_chrome": 24.0,         # the reflector bowls' bright chrome
    "rw_amber_lens": 24.0,          # indicators' amber
    "rw_wheel_alloy": 24.0,         # satin silver alloy wheels
    "rw_wheel_alloy_dark": 24.0,    # their spokes' shaded sides
    "rw_tyre": 24.0,                # matte tyre rubber
    "rw_tyre_dust": 24.0,           # the lowest third of the sidewall under road dust
    "rw_tyre_mark": 24.0,           # the sidewall's raised lettering, a shade lighter
    "rw_caliper": 24.0,             # cast brake calipers
    "rw_brake_disc": 24.0,          # a brake disc's turned steel, lightly rusted
    "rw_cab_screen": 24.0,          # the cab desks' displays, dimly lit
    "rw_cab_desk": 24.0,            # the EMU cab's dark grey desk
    "rw_cab_wall": 48.0,            # the cab's pale grey bulkhead and walls
    "rw_cab_ceiling": 48.0,         # the cab's ceiling under its dim lights
    "rw_cab_seat": 24.0,            # the driver's seat's blue-grey cloth
    "rw_lamp_field": 24.0,          # the EMU lamp clusters' satin grey field
    "rw_emu_grime": 1.0,            # grime streaks on the EMU's face (alpha tested, explicit UVs)
    "rw_sh2_red": 24.0,             # the Sh 2 board's red enamel, RAL 3020
    "rw_skip_yellow": 48.0,         # a skip's faded RAL 1021 enamel, rusted at its lips
    "rw_vending_body": 48.0,        # the snack machine's dark graphite powder coat
    "rw_container_code": 1.0,       # the container's owner code, type code and plates (explicit UVs, alpha tested)
}
PAINTS.update( PAINTS2 )

# The benches' sawn slat ends (railhead_bench): the gunsmith range's oak end grain, tinted to the varnished slats'
# brown and a shade darker, as end grain soaks up the finish. Explicit UVs.
PAINTS3 = {
    "rw_wood_end": 1.0,
}
PAINTS.update( PAINTS3 )
WOOD_END = "materials/gunsmith_range/bench_oak_endgrain"
WOOD_END_TINT = ( 0.72, 0.53, 0.35 )


def write_bench( root_or_out ):
    """ The bench paints (PAINTS3), into root/materials/railhead (or an out folder ending in materials/railhead). """
    out = Path( root_or_out )
    if out.name != "railhead":
        out = out / RESOURCE
    out.mkdir( parents=True, exist_ok=True )
    r, g, b = WOOD_END_TINT
    _write_text( out / "rw_wood_end.vmat", "\n".join( [
        "// Tools/railhead_prop_materials.py: the gunsmith range's oak end grain, tinted to Railhead's bench slats",
        '"Layer0"', "{", '    shader "shaders/complex.shader"', '    F_SPECULAR "1"', '    g_flMetalness "0"',
        '    g_flRoughnessScaleFactor "1"', f'    g_vColorTint "[{r:.3f} {g:.3f} {b:.3f} 1]"', '    g_flModelTintAmount "1"',
        f'    TextureColor "{WOOD_END}_color.png"', f'    TextureNormal "{WOOD_END}_normal.png"',
        f'    TextureRoughness "{WOOD_END}_roughness.png"', f'    TextureAmbientOcclusion "{DEFAULT_AO}"', "}" ] ) + "\n" )


def glass_vmat( tint, rough=0.05, absorb=0.15 ):
    """ glass.shader with what's behind showing through times tint (sRGB 0..1). """
    return "\n".join( [ "// Tools/railhead_prop_materials.py", '"Layer0"', "{", '    shader "shaders/glass.shader"',
                        '    F_GLASS_QUALITY "2"', '    g_bFogEnabled "1"', '    g_flBlurAmount "0"',
                        '    g_flRefractionStrength "1.002"', f'    AlbedoAbsorption "{absorb:.2f}"',
                        '    g_flTintColor "[1 1 1 0]"',
                        f'    TextureColor "[{tint[0]:.3f} {tint[1]:.3f} {tint[2]:.3f} 0]"',
                        '    TextureNormal "materials/default/default_normal.tga"',
                        f'    TextureRoughness "[{rough:.3f} {rough:.3f} {rough:.3f} 0]"',
                        '    TextureMetalness "[0 0 0 0]"', '    TextureAmbientOcclusion "[1 1 1 0]"',
                        '    TextureBlendMask "materials/default/default_blend.tga"',
                        '    TextureTintMask "materials/default/default.tga"',
                        '    TextureTranslucency "materials/default/default_trans.tga"', "}" ] ) + "\n"


# The container's markings atlas, 1024 x 512: name -> ( x0, y0, x1, y1 ) px, origin top left.
CODE_RECTS = {
    "owner": ( 0, 0, 1024, 150 ),           # HWLU 482913 7, the check digit boxed
    "type": ( 0, 170, 360, 300 ),           # 22G1
    "csc": ( 400, 170, 700, 470 ),          # the grey CSC safety approval plate
    "tare": ( 720, 170, 1024, 470 ),        # max gross / tare / net in kg and lb
}


def code_uv( name ):
    x0, y0, x1, y1 = CODE_RECTS[name]
    return [ ( x0 / 1024, 1 - y1 / 512 ), ( x1 / 1024, 1 - y1 / 512 ), ( x1 / 1024, 1 - y0 / 512 ), ( x0 / 1024, 1 - y0 / 512 ) ]


def write_round2( root_or_out ):
    """ The round-2 paints (PAINTS2), into root/materials/railhead (or straight into an out folder that already ends
    in materials/railhead). """
    from PIL import Image, ImageDraw
    out = Path( root_or_out )
    if out.name != "railhead":
        out = out / RESOURCE
    out.mkdir( parents=True, exist_ok=True )
    rng = np.random.default_rng( 70522 )
    for name, colour, metal, rough, illum in ( ( "rw_car_cloth", ( 62, 62, 64 ), 0.0, 0.9, 0.0 ),
                                               ( "rw_car_trim", ( 40, 41, 43 ), 0.0, 0.55, 0.0 ),
                                               ( "rw_car_headlining", ( 118, 117, 112 ), 0.0, 0.95, 0.0 ),
                                               ( "rw_car_chrome", ( 196, 198, 201 ), 1.0, 0.2, 0.0 ),
                                               ( "rw_lamp_chrome", ( 232, 233, 235 ), 1.0, 0.07, 0.0 ),
                                               ( "rw_amber_lens", ( 214, 118, 18 ), 0.0, 0.1, 0.0 ),
                                               ( "rw_wheel_alloy", ( 172, 175, 178 ), 0.9, 0.26, 0.0 ),
                                               ( "rw_wheel_alloy_dark", ( 92, 94, 97 ), 0.85, 0.36, 0.0 ),
                                               ( "rw_tyre", ( 30, 30, 31 ), 0.0, 0.86, 0.0 ),
                                               ( "rw_tyre_dust", ( 84, 76, 66 ), 0.0, 0.93, 0.0 ),
                                               ( "rw_tyre_mark", ( 58, 58, 59 ), 0.0, 0.78, 0.0 ),
                                               ( "rw_caliper", ( 66, 68, 70 ), 0.5, 0.5, 0.0 ),
                                               ( "rw_brake_disc", ( 122, 116, 108 ), 0.9, 0.45, 0.0 ),
                                               ( "rw_cab_screen", ( 40, 72, 92 ), 0.0, 0.2, 0.8 ),
                                               ( "rw_cab_desk", ( 54, 56, 59 ), 0.1, 0.6, 0.0 ),
                                               ( "rw_cab_wall", ( 176, 178, 176 ), 0.0, 0.7, 0.0 ),
                                               ( "rw_cab_ceiling", ( 160, 162, 160 ), 0.0, 0.8, 0.35 ),
                                               ( "rw_cab_seat", ( 44, 50, 66 ), 0.0, 0.85, 0.0 ),
                                               ( "rw_lamp_field", ( 104, 107, 110 ), 0.4, 0.32, 0.0 ),
                                               ( "rw_sh2_red", ( 176, 24, 18 ), 0.0, 0.3, 0.0 ),
                                               ( "rw_vending_body", ( 40, 41, 44 ), 0.1, 0.55, 0.0 ) ):
        _write_text( out / f"{name}.vmat", flat_vmat( colour, metal, rough, illum ) )
    # Retro-reflective sheeting after years on a buffer beam and a cone: scuffed, chipped at its edges, grimy.
    size = 512
    from PIL import ImageDraw as _D
    scuff = Image.new( "L", ( size, size ), 0 )
    sd = _D.Draw( scuff )
    for _ in range( 260 ):
        x, y = rng.uniform( 0, size, 2 )
        length, ang = rng.uniform( 6, 60 ), rng.normal( 0, 0.35 )
        sd.line( ( x, y, x + length * math.cos( ang ), y + length * math.sin( ang ) ), fill=int( rng.uniform( 60, 200 ) ),
                 width=int( rng.integers( 1, 3 ) ) )
    s_ = np.asarray( scuff, float ) / 255
    grime = np.clip( 0.18 + 0.12 * _field( rng, ( size, size ), 30 ) + 0.1 * _field( rng, ( size, size ), 4 ), 0, 0.5 )
    colour = np.array( ( 232, 232, 226 ), float )[None, None, :] * ( 1 - grime[..., None] ) \
        + np.array( ( 112, 104, 92 ) )[None, None, :] * grime[..., None]
    colour = colour * ( 1 - 0.35 * s_[..., None] ) + np.array( ( 150, 148, 140 ) ) * 0.35 * s_[..., None]
    _write_maps( out, "rw_reflective", colour, np.clip( 0.24 + 0.3 * s_ + 0.25 * grime, 0, 1 ), -0.004 * s_, 2.0 )
    _write_text( out / "rw_reflective.vmat", textured_vmat( "rw_reflective", 0.0 ) )
    _write_text( out / "rw_car_glass.vmat", glass_vmat( ( 0.66, 0.70, 0.72 ) ) )
    _write_text( out / "rw_emu_cab_glass.vmat", glass_vmat( ( 0.46, 0.49, 0.53 ), 0.04 ) )
    _write_text( out / "rw_lamp_lens.vmat", glass_vmat( ( 0.96, 0.97, 0.97 ), 0.02, 0.05 ) )
    # A skip's enamel: RAL 1021 faded towards cream, rust at the chips and run down from them, dirt high at the foot.
    size = 512
    colour, rough, height = worn_enamel( rng, size, ( 206, 158, 38 ), chips=0.03 )
    y = np.linspace( 0, 1, size )[:, None]                          # 0 at the top row
    foot = np.clip( ( y - 0.7 ) / 0.3, 0, 1 ) * ( 0.6 + 0.15 * _field( rng, ( size, size ), 10 ) )
    colour = colour * ( 1 - 0.55 * foot[..., None] ) + np.array( ( 92, 80, 64 ) ) * 0.55 * foot[..., None]
    _write_maps( out, "rw_skip_yellow", colour, np.clip( rough + 0.2 * foot, 0, 1 ), height, 3.0 )
    _write_text( out / "rw_skip_yellow.vmat", textured_vmat( "rw_skip_yellow", 0.15 ) )
    # Grime streaks: road dust and brake dust thrown up the face, ragged runs down from the screen's foot.
    h, w = 512, 256
    from scipy import ndimage
    col = ndimage.gaussian_filter( rng.normal( size=( 1, w ) ), ( 0, 3 ), mode="wrap" )[0]
    col = ( col - col.min() ) / ( col.max() - col.min() + 1e-6 )
    yy = np.linspace( 0, 1, h )[:, None]
    length = 0.35 + 0.6 * col[None, :]
    streak = np.clip( 1.0 - yy / length, 0, 1 ) ** 1.4
    noise = _field( rng, ( h, w ), ( 6, 1.2 ) )
    alpha = np.clip( streak * ( 0.75 + 0.35 * noise ) - 0.25, 0, 1 )
    colour = np.dstack( [ np.full( ( h, w ), c, float ) for c in ( 76, 66, 56 ) ] ) * ( 1 + 0.08 * noise )[..., None]
    _write_maps( out, "rw_emu_grime", colour, np.clip( 0.8 + 0.05 * noise, 0, 1 ), 0.0 * noise, 1.0 )
    _save( out / "rw_emu_grime_trans.png", Image.fromarray( np.clip( alpha * 255, 0, 255 ).astype( np.uint8 ), "L" ) )
    _write_text( out / "rw_emu_grime.vmat", textured_vmat( "rw_emu_grime", 0.0, alpha=True ) )
    # The container's markings: the owner code (made up: HW Logistik's U prefix, a serial and its check digit),
    # the size-type code, the CSC plate and the weights panel, white paint and a grey plate on alpha.
    img = Image.new( "RGB", ( 1024, 512 ), ( 236, 236, 230 ) )
    alpha = Image.new( "L", ( 1024, 512 ), 0 )
    draw, adraw = ImageDraw.Draw( img ), ImageDraw.Draw( alpha )
    big = _font( 108 )
    adraw.text( ( 14, 14 ), "HWLU 482913", font=big, fill=255 )
    tw = adraw.textlength( "HWLU 482913 ", font=big )
    adraw.text( ( 14 + tw + 10, 14 ), "7", font=big, fill=255 )
    adraw.rectangle( ( 14 + tw - 4, 12, 14 + tw + 82, 136 ), outline=255, width=7 )
    adraw.text( ( 14, 176 ), "22G1", font=_font( 104 ), fill=255 )
    draw.rectangle( ( 400, 170, 700, 470 ), fill=( 150, 152, 150 ) )
    adraw.rectangle( ( 400, 170, 700, 470 ), fill=255 )
    for k, line in enumerate( ( "CSC SAFETY APPROVAL", "D-HW-2149 / 08", "DATE MANUFACTURED", "03 / 2017",
                                "MAX GROSS 30480 KG", "STACKING 192000 KG", "RACKING 15240 KG" ) ):
        draw.text( ( 414, 184 + 38 * k ), line, font=_font( 24 ), fill=( 40, 42, 42 ) )
    for k, line in enumerate( ( "MAX GR. 30480 KG", "        67200 LB", "TARE    2230 KG", "         4920 LB",
                                "NET    28250 KG", "CU.CAP. 33.2 CU.M" ) ):
        adraw.text( ( 724, 184 + 46 * k ), line, font=_font( 30 ), fill=255 )
    _save( out / "rw_container_code_color.png", img )
    _save( out / "rw_container_code_trans.png", alpha )
    _write_maps( out, "rw_container_code", np.asarray( img, float ), np.full( ( 512, 1024 ), 0.6 ), np.zeros( ( 512, 1024 ) ) )
    _write_text( out / "rw_container_code.vmat", textured_vmat( "rw_container_code", 0.0, alpha=True ) )


CASE_GLASS = """// Tools/railhead_prop_materials.py
"Layer0"
{
    shader "shaders/glass.shader"
    F_GLASS_QUALITY "2"
    g_bFogEnabled "1"
    g_flBlurAmount "0"
    g_flRefractionStrength "1.002"
    AlbedoAbsorption "0.15"
    g_flTintColor "[1 1 1 0]"
    TextureColor "[0.94 0.96 0.95 0]"
    TextureNormal "materials/default/default_normal.tga"
    TextureRoughness "[0.04 0.04 0.04 0]"
    TextureMetalness "[0 0 0 0]"
    TextureAmbientOcclusion "[1 1 1 0]"
    TextureBlendMask "materials/default/default_blend.tga"
    TextureTintMask "materials/default/default.tga"
    TextureTranslucency "materials/default/default_trans.tga"
}
"""


def _atlas_vmat( atlas, tint, alpha=False, illum=0.0 ):
    """ Another atlas's colour picture under this tint: alpha tested on its translucency, or self-lit all over. """
    lines = [ "// Tools/railhead_prop_materials.py", '"Layer0"', "{", '    shader "shaders/complex.shader"',
              '    F_SPECULAR "1"' ]
    if alpha:
        lines += [ '    F_ALPHA_TEST "1"', '    g_flAlphaTestReference "0.5"', '    g_flAntiAliasedEdgeStrength "1"',
                   f'    TextureTranslucency "{RESOURCE}/{atlas}_trans.png"' ]
    if illum:
        lines += [ '    F_SELF_ILLUM "1"', '    TextureSelfIllumMask "[1.000000 1.000000 1.000000 0.000000]"',
                   f'    g_flSelfIllumBrightness "{illum:.2f}"', '    g_flSelfIllumAlbedoFactor "1.0"',
                   '    g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"' ]
    lines += [ '    g_flRoughnessScaleFactor "1"', '    g_flMetalness "0.00"',
               f'    TextureColor "{RESOURCE}/{atlas}_color.png"', '    TextureNormal "materials/default/default_normal.tga"',
               '    TextureRoughness "[0.400000 0.400000 0.400000 0.000000]"', f'    TextureAmbientOcclusion "{DEFAULT_AO}"',
               f'    g_vColorTint "[{tint[0]:.6f} {tint[1]:.6f} {tint[2]:.6f} 1.000000]"', '    g_flModelTintAmount "1.0"', "}" ]
    return "\n".join( lines ) + "\n"


def missing( root ):
    """ True if any of the materials is missing under root (never Assets by default: give it the root to check). """
    out = Path( root ) / RESOURCE
    return any( not ( out / f"{p}.vmat" ).exists() for p in PAINTS )


def main():
    ap = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    ap.add_argument( "--out", required=True, type=Path, help="a root laid out as Assets (a stage folder, or Assets)" )
    ap.add_argument( "--round2", action="store_true", help="only the round-2 paints (PAINTS2)" )
    ap.add_argument( "--bench", action="store_true", help="only the bench paints (PAINTS3)" )
    args = ap.parse_args()
    if args.bench:
        write_bench( args.out )
    elif args.round2:
        write_round2( args.out )
    else:
        write( args.out )


if __name__ == "__main__":
    main()
