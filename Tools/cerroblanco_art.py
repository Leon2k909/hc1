"""
Cerro Blanco's exhibitions, drawn for Tools/cerroblanco_fitout.py: the paintings and drawings on the museum's walls,
the shows' wall texts, the works' labels and the museum's signs. All of it is made up (the artists, their works and the
texts, in Spanish: the museum is on a hill above a Mexican town), drawn with numpy, scipy and PIL in the project's own
fonts.

    python Tools/cerroblanco_art.py [--out <dir>] [--only art|text|signs ...] [--sheet <png>]

The four shows on the museum's banners (cerroblanco_materials.BANNERS) fill its galleries:
- ROSTROS (portraits 1900-1960), the West Gallery: modernist portraits in flat planes of strong colour.
- MAREAS (paintings of the coast), the North Gallery: seas and skies in thick horizontal strokes.
- TIERRA ROJA (landscapes of the plateau), the South Gallery: mesas, agaves and red earth.
- FORMA Y VACIO (20th-century sculpture), the East Hall: the sculptors' charcoal studies, framed under white mats.
And two colour-field canvases for the rotunda and the cafe's upper room.

A painting is drawn as flat shapes at twice its size, then painted: its colours are smeared a few pixels along a
stroke field (a line integral convolution, as a brush drags wet paint), streaked by the same strokes' noise, and laid on
a canvas weave. The strokes also give its height, so the normal map shows the impasto.

Writes <out>/materials/cerroblanco/fitout/ (out defaults to Assets):
- art_color.png (4096 square: 4 x 4 cells of 1024, each work at its own shape in its cell with its edges carried out to
  the cell's, so the mipmaps don't bleed one work into the next), art_normal.png, art_rough.png (2048) and cb_art.vmat;
- walltext_color.png / walltext_trans.png (2048 square: each show's title, subtitle and introduction in grey vinyl
  letters, alpha tested) and cb_walltext.vmat;
- signs_color.png (2048 square: the wayfinding panels, the room plates, the labels, the opening hours) and
  cb_signs.vmat; exit_color.png and cb_exit.vmat (the green SALIDA signs, self-lit);
- layout.json: where each work, text and sign is in its sheet, read by the fit-out for its UVs.
A file is only rewritten when it changes (map_kit.write_text, and PNGs compared before saving), so a re-run doesn't
make the editor recompile what's the same.
"""
import argparse
import json
import math
import os
import platform
from pathlib import Path

# SciPy's optional CPU feature discovery can hang in Windows WMI on this machine.
platform.machine = lambda: os.environ.get( "PROCESSOR_ARCHITECTURE", "AMD64" )
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, map_coordinates, zoom

ROOT = Path( __file__ ).resolve().parent.parent
FONTS = ROOT / "Assets/fonts"
RESOURCE = "materials/cerroblanco/fitout"
CELL = 1024
WORK = 944                     # a work's longer side in its cell: 40 pixels of carried-out edge all round

# ---------------------------------------------------------------------------------------------------------------------
# The works: ( key, show, artist, life, title, year, technique, aspect w/h, generator, seed )

ARTISTS = {
    "rios": ( "Elena Ríos Arteaga", "1908 – 1974" ),
    "villasenor": ( "Tomás Villaseñor", "1899 – 1966" ),
    "lucero": ( "Amparo Lucero", "1915 – 1991" ),
    "beltran": ( "Julián Beltrán Ochoa", "1904 – 1980" ),
    "iturbe": ( "Rafael Iturbe", "1911 – 1978" ),
    "andrade": ( "Consuelo Andrade", "1920 – 2003" ),
    "peralta": ( "Ignacio Peralta", "1906 – 1969" ),
    "zamudio": ( "Dolores Zamudio", "1918 – 1999" ),
    "montoya": ( "Andrés Montoya Gil", "1902 – 1977" ),
    "quiroga": ( "Esteban Quiroga", "1925 – 2010" ),
    "garay": ( "Lucía Garay", "1913 – 1988" ),
    "elizondo": ( "Martín Elizondo", "1921 – 2002" ),
    "ortiz": ( "Samuel Ortiz Reyes", "1930 – 2015" ),
}
OIL = "Óleo sobre tela"
CHARCOAL = "Carbón sobre papel"
ACRYLIC = "Acrílico sobre tela"
WORKS = [
    ( "rostro_rebozo", "rostros", "rios", "Muchacha con rebozo azul", 1934, OIL, 0.8, "portrait", 11 ),
    ( "rostro_maestro", "rostros", "villasenor", "El maestro de música", 1928, OIL, 0.75, "portrait", 12 ),
    ( "rostro_hermana", "rostros", "lucero", "Retrato de mi hermana", 1947, OIL, 0.8, "portrait", 13 ),
    ( "rostro_sombrero", "rostros", "beltran", "Autorretrato con sombrero", 1939, OIL, 0.75, "portrait", 14 ),
    ( "marea_punta", "mareas", "iturbe", "Marea alta en Punta Roca", 1936, OIL, 1.33, "sea", 21 ),
    ( "marea_violeta", "mareas", "andrade", "Tarde violeta", 1951, OIL, 1.25, "sea", 22 ),
    ( "marea_barcas", "mareas", "peralta", "Barcas al amanecer", 1942, OIL, 1.5, "sea", 23 ),
    ( "marea_ola", "mareas", "iturbe", "La ola", 1940, OIL, 2.0, "sea", 24 ),
    ( "tierra_mesa", "tierra", "zamudio", "Mesa de los Cuervos", 1946, OIL, 1.4, "plateau", 31 ),
    ( "tierra_magueyes", "tierra", "montoya", "Magueyes", 1931, OIL, 0.8, "plateau", 32 ),
    ( "tierra_roja", "tierra", "zamudio", "Tierra roja II", 1958, OIL, 1.25, "plateau", 33 ),
    ( "tierra_camino", "tierra", "quiroga", "Camino a la sierra", 1955, OIL, 1.6, "plateau", 34 ),
    ( "forma_vacio", "forma", "garay", "Estudio para «Vacío»", 1962, CHARCOAL, 0.78, "drawing", 41 ),
    ( "forma_torso", "forma", "elizondo", "Estudio de torso", 1957, CHARCOAL, 0.78, "drawing", 42 ),
    ( "campo_4", "campo", "ortiz", "Campo de color núm. 4", 1968, ACRYLIC, 0.8, "field", 51 ),
    ( "campo_7", "campo", "ortiz", "Campo de color núm. 7", 1971, ACRYLIC, 0.8, "field", 52 ),
]

SHOWS = {
    # key: ( title, subtitle, introduction, where )
    "rostros": ( "ROSTROS", "retratos 1900 — 1960",
                 "Entre 1900 y 1960, los pintores de la región dejaron atrás el retrato de salón y miraron a sus "
                 "vecinos: campesinas, maestros, músicos y niños, pintados con planos de color y sin adornos. Esta "
                 "exposición reúne cuarenta obras de colecciones públicas y privadas; muchas se exhiben por primera "
                 "vez.", "Galería Oeste" ),
    "mareas": ( "MAREAS", "pintura de la costa",
                "El mar llegó tarde a la pintura de la meseta. Los artistas que bajaron a la costa en los años treinta "
                "encontraron otra luz: blanca al mediodía, violeta al caer la tarde. Estas telas, pintadas al aire libre "
                "y con pinceladas gruesas, siguen el ir y venir de las mareas a lo largo de una sola temporada.",
                "Galería Norte" ),
    "tierra": ( "TIERRA ROJA", "paisajes de la meseta",
                "La tierra roja, los magueyes y las mesas de piedra fueron el tema de una generación que pintó el "
                "paisaje como un retrato del país. Las obras de esta sala van del apunte del natural a una abstracción "
                "casi total, sin perder nunca la línea del horizonte.", "Galería Sur" ),
    "forma": ( "FORMA Y VACÍO", "escultura del siglo XX",
               "La escultura del siglo XX aprendió a trabajar con el aire. Las piezas de esta sala, en bronce, acero y "
               "piedra, se definen tanto por su masa como por los huecos que la atraviesan. Los dibujos preparatorios, "
               "expuestos por primera vez, muestran cómo cada forma nació de una línea.", "Sala Este" ),
}
CREDIT = "Con el apoyo de la Fundación Cerro Blanco y del Patronato del Museo"
MENU = [ ( "CAFÉ", [ ( "Americano", "$35" ), ( "Capuchino", "$45" ), ( "Latte", "$48" ), ( "Chocolate", "$42" ) ] ),
         ( "PAN DULCE", [ ( "Concha", "$25" ), ( "Cuernito", "$28" ), ( "Galletas", "$20" ), ( "Agua fresca", "$30" ) ] ) ]

# The signs: wayfinding panels (white on charcoal), room plates, the opening hours and the house rules.
WAYFINDING = [
    ( "way_oeste", "←", "GALERÍA OESTE", "Rostros" ),
    ( "way_norte", "→", "GALERÍA NORTE", "Mareas" ),
    ( "way_este", "→", "SALA ESTE", "Forma y vacío" ),
    ( "way_sur", "↓", "GALERÍA SUR", "Tierra roja" ),
    ( "way_cafe", "→", "CAFETERÍA", "Terraza · primer piso" ),
    ( "way_info", "i", "INFORMACIÓN", "Taquilla · guardarropa" ),
    ( "way_salida", "←", "SALIDA", "Estacionamiento" ),
    ( "way_salas", "↑", "SALAS 1 — 8", "Exposiciones temporales" ),
]
ROOMS = [ "SALA 1", "SALA 2", "SALA 3", "SALA 4", "SALA 5", "SALA 6", "SALA 7", "SALA 8", "ROTONDA", "CAFETERÍA",
          "PRIVADO", "MONTAJE" ]
PLATES = [
    ( "hours", "MARTES A DOMINGO", "10:00 — 18:00  ·  LUNES CERRADO" ),
    ( "rules", "NO TOCAR LAS OBRAS", "No se permiten fotografías con flash" ),
    ( "logo", "MUSEO CERRO BLANCO", "Colección permanente y exposiciones temporales" ),
    ( "staff", "SOLO PERSONAL", "Área de montaje y bodega" ),
]


# ---------------------------------------------------------------------------------------------------------------------
# Helpers

def font( name, size ):
    return ImageFont.truetype( str( FONTS / name ), size )


def srgb( c ):
    return np.asarray( c, np.float32 ) / 255.0


def save_png( path, array, mode="RGB" ):
    """ Saves a 0..1 float array (or uint8) as a PNG, only if its pixels changed. """
    a = array if array.dtype == np.uint8 else np.clip( np.rint( array * 255.0 ), 0, 255 ).astype( np.uint8 )
    image = Image.fromarray( a, mode if a.ndim == 3 else "L" )
    if path.exists():
        try:
            with Image.open( path ) as old:
                if old.size == image.size and old.mode == image.mode and np.array_equal( np.asarray( old ), a ):
                    return False
        except OSError:
            pass
    temp = path.with_name( path.name + ".writing" )
    image.save( temp, format="PNG", optimize=False, compress_level=6 )
    temp.replace( path )
    return True


def write_text( path, text ):
    if path.exists() and path.read_text( encoding="utf-8" ) == text:
        return
    temp = path.with_name( path.name + ".writing" )
    temp.write_text( text, encoding="utf-8", newline="\n" )
    temp.replace( path )


def gl_normal( height, strength ):
    gy, gx = np.gradient( height.astype( np.float32 ) )
    n = np.stack( [ -gx * strength, gy * strength, np.ones_like( gx ) ], -1 )
    n /= np.linalg.norm( n, axis=-1, keepdims=True )
    return n * 0.5 + 0.5


def field( rng, h, w, scale, smooth=2.0 ):
    """ Smooth noise, about scale pixels between features, unit variance. """
    small = rng.standard_normal( ( max( 2, h // scale + 2 ), max( 2, w // scale + 2 ) ) ).astype( np.float32 )
    small = gaussian_filter( small, smooth )
    big = zoom( small, ( h / ( small.shape[0] - 2 ), w / ( small.shape[1] - 2 ) ), order=3 )[:h, :w]
    big -= big.mean()
    return big / max( float( big.std() ), 1e-6 )


def lic( channels, angle, steps, step=1.0 ):
    """ Line integral convolution: each channel averaged along the stroke field's lines, steps each way. """
    h, w = angle.shape
    yy, xx = np.mgrid[0:h, 0:w].astype( np.float32 )
    total = [ c.astype( np.float32 ).copy() for c in channels ]
    count = 1
    for sign in ( 1.0, -1.0 ):
        px, py = xx.copy(), yy.copy()
        for k in range( steps ):
            a = map_coordinates( angle, [ py, px ], order=1, mode="nearest" )
            px += sign * np.cos( a ) * step
            py += sign * np.sin( a ) * step
            for t, c in zip( total, channels ):
                t += map_coordinates( c, [ py, px ], order=1, mode="reflect" )
            count += 1
    return [ t / count for t in total ]


class Canvas:
    """ A picture drawn at k times its size in flat shapes (anti-aliased by the downsample), in linear-ish 0..1 sRGB. """

    def __init__( self, w, h, colour, k=2 ):
        self.w, self.h, self.k = w, h, k
        self.rgb = np.ones( ( h * k, w * k, 3 ), np.float32 ) * srgb( colour )

    def mask( self, draw ):
        image = Image.new( "L", ( self.w * self.k, self.h * self.k ), 0 )
        draw( ImageDraw.Draw( image ), self.k )
        return np.asarray( image, np.float32 ) / 255.0

    def fill( self, mask, colour, alpha=1.0 ):
        c = np.asarray( colour, np.float32 )
        if c.ndim == 1:
            c = c[None, None, :]
        if c.max() > 1.0:
            c = c / 255.0
        m = ( mask * alpha )[..., None]
        self.rgb = self.rgb * ( 1 - m ) + c * m

    def poly( self, points, colour, alpha=1.0, blur=0.0 ):
        k = self.k
        m = self.mask( lambda d, k: d.polygon( [ ( x * k, y * k ) for x, y in points ], fill=255 ) )
        if blur:
            m = gaussian_filter( m, blur * k )
        self.fill( m, colour, alpha )
        return m

    def ellipse( self, box, colour, alpha=1.0, blur=0.0 ):
        x0, y0, x1, y1 = box
        m = self.mask( lambda d, k: d.ellipse( ( x0 * k, y0 * k, x1 * k, y1 * k ), fill=255 ) )
        if blur:
            m = gaussian_filter( m, blur * self.k )
        self.fill( m, colour, alpha )
        return m

    def rect( self, box, colour, alpha=1.0, blur=0.0 ):
        x0, y0, x1, y1 = box
        return self.poly( [ ( x0, y0 ), ( x1, y0 ), ( x1, y1 ), ( x0, y1 ) ], colour, alpha, blur )

    def line( self, points, colour, width, alpha=1.0, blur=0.0 ):
        k = self.k
        m = self.mask( lambda d, k: d.line( [ ( x * k, y * k ) for x, y in points ], fill=255, width=max( 1, int( width * k ) ),
                                            joint="curve" ) )
        if blur:
            m = gaussian_filter( m, blur * k )
        self.fill( m, colour, alpha )
        return m

    def result( self ):
        image = Image.fromarray( np.clip( np.rint( self.rgb * 255 ), 0, 255 ).astype( np.uint8 ), "RGB" )
        return np.asarray( image.resize( ( self.w, self.h ), Image.LANCZOS ), np.float32 ) / 255.0


def dabs( rgb, rng, angle, count, length=( 9.0, 22.0 ), width=( 2.5, 6.0 ), jitter=0.05, alpha=( 0.55, 0.9 ) ):
    """ Brush dabs laid over the picture: each a short tapered stroke along the brush's direction in the colour under
    it, a little lighter, darker or warmer, shorter where the picture has detail so the features keep their edges. """
    h, w, _ = rgb.shape
    luma = rgb @ np.array( ( 0.2126, 0.7152, 0.0722 ), np.float32 )
    gy, gx = np.gradient( gaussian_filter( luma, 1.0 ) )
    edge = np.clip( np.hypot( gx, gy ) / ( np.percentile( np.hypot( gx, gy ), 98 ) + 1e-6 ), 0, 1 )
    k = 2
    layer = Image.new( "RGBA", ( w * k, h * k ), ( 0, 0, 0, 0 ) )
    d = ImageDraw.Draw( layer )
    xs, ys = rng.uniform( 0, w - 1, count ), rng.uniform( 0, h - 1, count )
    lengths, widths = rng.uniform( *length, count ), rng.uniform( *width, count )
    alphas = rng.uniform( *alpha, count )
    shifts = rng.normal( 0, jitter, ( count, 3 ) ) + rng.normal( 0, jitter * 0.6, ( count, 1 ) )
    for x, y, L, W, a_, shift in zip( xs, ys, lengths, widths, alphas, shifts ):
        i, j = int( y ), int( x )
        detail = edge[i, j]
        if detail > 0.55:
            continue
        L *= 1 - 0.75 * detail
        W *= 1 - 0.5 * detail
        a = float( angle[i, j] )
        ux, uy = math.cos( a ), math.sin( a )
        col = np.clip( rgb[i, j] * ( 1 + shift ), 0, 1 )
        # A tapered stroke: blunt where the brush lands, thinning as it lifts.
        pts = []
        for t, half in ( ( -0.5, 0.35 ), ( -0.42, 0.85 ), ( -0.15, 1.0 ), ( 0.2, 0.92 ), ( 0.42, 0.55 ), ( 0.5, 0.12 ) ):
            pts.append( ( ( x + ux * L * t - uy * W * half / 2 ) * k, ( y + uy * L * t + ux * W * half / 2 ) * k ) )
        for t, half in ( ( 0.5, 0.12 ), ( 0.42, 0.55 ), ( 0.2, 0.92 ), ( -0.15, 1.0 ), ( -0.42, 0.85 ), ( -0.5, 0.35 ) ):
            pts.append( ( ( x + ux * L * t + uy * W * half / 2 ) * k, ( y + uy * L * t - ux * W * half / 2 ) * k ) )
        d.polygon( pts, fill=( int( col[0] * 255 ), int( col[1] * 255 ), int( col[2] * 255 ), int( a_ * 255 ) ) )
    over = np.asarray( layer.resize( ( w, h ), Image.LANCZOS ), np.float32 ) / 255.0
    return rgb * ( 1 - over[..., 3:] ) + over[..., :3] * over[..., 3:]


def face( c, cx, cy, rw, rh, turn, skin, shade, hair, lips=( 150, 62, 56 ), old=False, mustache=False, glasses=False,
          brim_shadow=0.0 ):
    """ A head in planes: lit from the upper left, the shaded plane right of the nose, almond eyes under heavy lids,
    the nose's shadow, two-tone lips, the chin's shadow on the neck. turn -1..1 looks to the viewer's left..right. """
    shade = np.asarray( shade, np.float32 )
    pts = []
    for j in range( 48 ):
        t = 2 * math.pi * j / 48
        narrow = 1 - 0.2 * max( 0.0, math.sin( t ) ) ** 1.5
        pts.append( ( cx + rw * math.cos( t ) * narrow, cy + rh * math.sin( t ) ) )
    head = c.poly( pts, skin )
    # The shaded plane: right of a line down the forehead, the nose and the chin.
    nose = cx + rw * ( 0.18 + 0.32 * turn )
    plane = c.mask( lambda d, k: d.polygon( [ ( ( nose + rw * 0.05 ) * k, ( cy - rh * 1.2 ) * k ), ( ( cx + rw * 1.3 ) * k, ( cy - rh * 1.2 ) * k ),
                                              ( ( cx + rw * 1.3 ) * k, ( cy + rh * 1.3 ) * k ), ( ( nose - rw * 0.25 ) * k, ( cy + rh * 1.3 ) * k ),
                                              ( ( nose - rw * 0.05 ) * k, ( cy + rh * 0.45 ) * k ), ( ( nose + rw * 0.1 ) * k, ( cy + rh * 0.05 ) * k ) ],
                                            fill=255 ) )
    c.fill( head * gaussian_filter( plane, 2.5 * c.k ), shade, 0.85 )
    if brim_shadow:
        band = c.mask( lambda d, k: d.rectangle( ( 0, 0, c.w * k, ( cy - rh * brim_shadow ) * k ), fill=255 ) )
        c.fill( head * gaussian_filter( band, 4 * c.k ), shade * 0.82, 0.8 )
    # Cheeks warmed, the eye sockets darkened.
    for s in ( -1, 1 ):
        ex = cx + s * rw * 0.4 + turn * rw * 0.28
        c.ellipse( ( ex - rw * 0.3, cy + rh * 0.08, ex + rw * 0.25, cy + rh * 0.4 ), ( 200, 96, 80 ), 0.18, blur=8 )
        c.ellipse( ( ex - rw * 0.3, cy - rh * 0.28, ex + rw * 0.3, cy + rh * 0.06 ), shade * 0.85, 0.35, blur=6 )
    # Eyes: almond shapes under a lid line, the far one smaller; a glint in each.
    for s in ( -1, 1 ):
        far = ( s > 0 ) == ( turn > 0 )
        scale = 0.82 if far and abs( turn ) > 0.15 else 1.0
        ex = cx + s * rw * 0.4 * ( 1 - 0.35 * abs( turn ) if far else 1 ) + turn * rw * 0.28
        ey = cy - rh * 0.1
        ew, eh = rw * 0.25 * scale, rh * 0.075 * scale
        almond = [ ( ex - ew, ey ), ( ex - ew * 0.5, ey - eh * 0.95 ), ( ex + ew * 0.35, ey - eh ), ( ex + ew, ey - eh * 0.1 ),
                   ( ex + ew * 0.4, ey + eh * 0.75 ), ( ex - ew * 0.5, ey + eh * 0.7 ) ]
        c.poly( almond, ( 224, 214, 198 ) )
        c.ellipse( ( ex - ew * 0.45, ey - eh * 0.95, ex + ew * 0.4, ey + eh * 0.75 ), ( 46, 32, 26 ) )
        c.ellipse( ( ex - ew * 0.12, ey - eh * 0.55, ex + ew * 0.05, ey - eh * 0.2 ), ( 236, 230, 220 ), 0.85 )
        c.line( [ ( ex - ew * 1.08, ey + eh * 0.1 ), ( ex - ew * 0.5, ey - eh * 1.1 ), ( ex + ew * 0.4, ey - eh * 1.12 ), ( ex + ew * 1.05, ey - eh * 0.1 ) ],
                ( 40, 28, 24 ), max( 1.5, rw * 0.028 ) )
        brow = [ ( ex - ew * 1.15, ey - eh * 2.1 ), ( ex - ew * 0.2, ey - eh * 3.1 ), ( ex + ew * 1.1, ey - eh * 2.4 ),
                 ( ex + ew * 1.1, ey - eh * 2.0 ), ( ex - ew * 0.2, ey - eh * 2.55 ), ( ex - ew * 1.1, ey - eh * 1.75 ) ]
        c.poly( brow, np.asarray( hair, np.float32 ) * ( 1.3 if old else 1.0 ) + ( 60 if old else 0 ) )
        if glasses:
            r = ew * 1.35
            c.line( [ ( ex + r * math.cos( 2 * math.pi * j / 24 ), ey + r * 0.85 * math.sin( 2 * math.pi * j / 24 ) ) for j in range( 25 ) ],
                    ( 36, 30, 28 ), max( 1.2, rw * 0.02 ) )
    if glasses:
        c.line( [ ( cx - rw * 0.08 + turn * rw * 0.28, cy - rh * 0.12 ), ( cx + rw * 0.08 + turn * rw * 0.28, cy - rh * 0.12 ) ],
                ( 36, 30, 28 ), max( 1.2, rw * 0.02 ) )
    # The nose: its shaded side, the nostrils, a light on its tip.
    c.poly( [ ( nose, cy - rh * 0.05 ), ( nose + rw * 0.13, cy + rh * 0.3 ), ( nose - rw * 0.02, cy + rh * 0.36 ), ( nose - rw * 0.06, cy + rh * 0.3 ) ],
            shade * 0.78, 0.9 )
    c.ellipse( ( nose - rw * 0.16, cy + rh * 0.3, nose - rw * 0.04, cy + rh * 0.36 ), shade * 0.55, 0.9 )
    c.ellipse( ( nose + rw * 0.02, cy + rh * 0.3, nose + rw * 0.12, cy + rh * 0.36 ), shade * 0.55, 0.9 )
    c.ellipse( ( nose - rw * 0.14, cy + rh * 0.18, nose - rw * 0.04, cy + rh * 0.25 ), np.asarray( skin ) * 1.15, 0.6, blur=1.5 )
    if mustache:
        c.poly( [ ( cx - rw * 0.36 + turn * rw * 0.2, cy + rh * 0.5 ), ( cx - rw * 0.1 + turn * rw * 0.2, cy + rh * 0.4 ),
                  ( cx + rw * 0.12 + turn * rw * 0.2, cy + rh * 0.4 ), ( cx + rw * 0.36 + turn * rw * 0.2, cy + rh * 0.5 ),
                  ( cx + rw * 0.2 + turn * rw * 0.2, cy + rh * 0.47 ), ( cx - rw * 0.2 + turn * rw * 0.2, cy + rh * 0.47 ) ],
                ( 150, 146, 140 ) if old else hair )
    mx = cx + turn * rw * 0.22
    lips = np.asarray( lips, np.float32 )
    c.poly( [ ( mx - rw * 0.24, cy + rh * 0.53 ), ( mx - rw * 0.08, cy + rh * 0.48 ), ( mx, cy + rh * 0.5 ), ( mx + rw * 0.08, cy + rh * 0.48 ),
              ( mx + rw * 0.24, cy + rh * 0.53 ), ( mx, cy + rh * 0.55 ) ], lips * 0.75 )
    c.poly( [ ( mx - rw * 0.22, cy + rh * 0.535 ), ( mx, cy + rh * 0.555 ), ( mx + rw * 0.22, cy + rh * 0.535 ), ( mx + rw * 0.1, cy + rh * 0.63 ),
              ( mx - rw * 0.1, cy + rh * 0.63 ) ], lips )
    c.ellipse( ( mx - rw * 0.25, cy + rh * 0.7, mx + rw * 0.25, cy + rh * 0.86 ), shade * 0.9, 0.35, blur=4 )
    if old:
        for s in ( -1, 1 ):
            c.line( [ ( mx + s * rw * 0.3, cy + rh * 0.3 ), ( mx + s * rw * 0.36, cy + rh * 0.5 ), ( mx + s * rw * 0.3, cy + rh * 0.66 ) ],
                    shade * 0.7, max( 1.0, rw * 0.02 ), alpha=0.6 )
    return head


def paint( rgb, rng, angle, smear=2, stroke=14, streak=0.035, weave=0.018, impasto=1.0, dab_count=9000,
           dab_length=( 9.0, 22.0 ), dab_width=( 2.5, 6.0 ), dab_jitter=0.05 ):
    """ Wet paint: the colours smeared a little along the brush's direction, laid over with brush dabs, the bristles'
    streaks along each stroke and a canvas weave under it all. Returns the colour, its height (for the normal map) and
    a roughness. """
    h, w, _ = rgb.shape
    if smear:
        rgb = np.stack( lic( [ rgb[..., c] for c in range( 3 ) ], angle, smear, 1.0 ), -1 )
    if dab_count:
        rgb = dabs( rgb, rng, angle, dab_count, dab_length, dab_width, dab_jitter )
    # The bristles: blurred noise dragged along the strokes, so each mark is a band of fine parallel grooves.
    noise = gaussian_filter( rng.standard_normal( ( h, w ) ).astype( np.float32 ), 0.9 )
    bristles = lic( [ noise ], angle, stroke )[0]
    bristles = ( bristles - bristles.mean() ) / max( float( bristles.std() ), 1e-6 )
    yy, xx = np.mgrid[0:h, 0:w].astype( np.float32 )
    cloth = np.sin( xx * 2.3 ) * np.sin( yy * 2.3 )
    luma = rgb @ np.array( ( 0.2126, 0.7152, 0.0722 ), np.float32 )
    # Paint is thicker in the lights (lead white is laid on thick) and where dabs overlap (local contrast).
    ridges = luma - gaussian_filter( luma, 3.0 )
    out = rgb * ( 1 + streak * bristles[..., None] ) * ( 1 + weave * cloth[..., None] )
    height = impasto * ( 0.55 * bristles * ( 0.4 + 0.9 * luma ) + 9.0 * ridges ) + 0.3 * cloth
    rough = np.clip( 0.5 - 0.05 * bristles - 0.08 * luma + 0.4 * np.abs( ridges ), 0.32, 0.72 )
    return np.clip( out, 0, 1 ), height.astype( np.float32 ), rough.astype( np.float32 )


def stroke_angle( rng, h, w, base, wobble, scale=60, rgb=None, follow=0.75 ):
    """ The brush's direction at each pixel: base turned by smooth noise, and, where the picture has an edge, along
    that edge (the structure tensor's tangent, weighted by how clear the edge is), as a painter follows a form. """
    angle = base + wobble * field( rng, h, w, scale )
    if rgb is None:
        return angle.astype( np.float32 )
    luma = gaussian_filter( rgb @ np.array( ( 0.2126, 0.7152, 0.0722 ), np.float32 ), 1.2 )
    gy, gx = np.gradient( luma )
    jxx, jyy, jxy = ( gaussian_filter( a, 7 ) for a in ( gx * gx, gy * gy, gx * gy ) )
    tangent = 0.5 * np.arctan2( 2 * jxy, jxx - jyy ) + math.pi / 2
    root = np.sqrt( ( jxx - jyy ) ** 2 + 4 * jxy ** 2 )
    coherence = np.clip( root / ( jxx + jyy + 1e-6 ), 0, 1 ) ** 2
    strength = np.clip( ( jxx + jyy ) / ( np.percentile( jxx + jyy, 90 ) + 1e-9 ), 0, 1 )
    weight = follow * coherence * strength
    # Blend in double-angle space, so directions half a turn apart agree.
    cx = ( 1 - weight ) * np.cos( 2 * angle ) + weight * np.cos( 2 * tangent )
    cy = ( 1 - weight ) * np.sin( 2 * angle ) + weight * np.sin( 2 * tangent )
    return ( 0.5 * np.arctan2( cy, cx ) ).astype( np.float32 )


# ---------------------------------------------------------------------------------------------------------------------
# The genres

def portrait( rng, w, h, variant=None ):
    """ A modernist portrait, one of four compositions: a girl in a blue rebozo before a window, an old music teacher
    with his guitar, a sister with flowers in her hair before banana leaves, a self-portrait in a palm hat on the
    plateau. Flat planes of colour, then painted. """
    skin, shade = ( 186, 128, 96 ), ( 128, 82, 62 )
    hair = ( 30, 24, 22 )
    if variant == "rostro_rebozo":
        c = Canvas( w, h, ( 190, 104, 68 ) )
        c.rect( ( 0, h * 0.7, w, h ), ( 150, 76, 52 ) )
        c.rect( ( w * 0.06, h * 0.06, w * 0.36, h * 0.42 ), ( 236, 222, 196 ) )
        c.rect( ( w * 0.08, h * 0.08, w * 0.34, h * 0.4 ), ( 118, 168, 204 ) )
        c.poly( [ ( w * 0.08, h * 0.4 ), ( w * 0.08, h * 0.32 ), ( w * 0.18, h * 0.28 ), ( w * 0.26, h * 0.33 ), ( w * 0.34, h * 0.3 ),
                  ( w * 0.34, h * 0.4 ) ], ( 120, 132, 104 ) )
        c.rect( ( w * 0.2, h * 0.06, w * 0.22, h * 0.42 ), ( 236, 222, 196 ) )
        cx, cy, rw, rh = w * 0.52, h * 0.4, w * 0.15, h * 0.135
        blue = ( 34, 70, 132 )
        # The rebozo over her head and round her shoulders, its striped ends hanging down.
        c.ellipse( ( cx - rw * 1.55, cy - rh * 1.45, cx + rw * 1.5, cy + rh * 1.3 ), blue )
        c.poly( [ ( cx - rw * 1.5, cy - rh * 0.2 ), ( cx + rw * 1.5, cy - rh * 0.2 ), ( w * 0.92, h ), ( w * 0.08, h ) ], blue )
        c.poly( [ ( cx - rw * 1.5, cy ), ( cx - rw * 0.6, cy + rh * 1.6 ), ( w * 0.36, h ), ( w * 0.08, h ) ], np.array( blue ) * 0.72 )
        for j in range( 7 ):
            y = h * ( 0.84 + 0.022 * j )
            c.line( [ ( w * 0.08, y ), ( w * 0.92, y ) ], ( 226, 224, 216 ) if j % 2 else ( 168, 40, 44 ), 3, alpha=0.8 )
        c.rect( ( cx - rw * 0.42, cy + rh * 0.6, cx + rw * 0.42, cy + rh * 1.2 ), shade )
        c.poly( [ ( cx - rw * 0.6, cy + rh * 1.1 ), ( cx + rw * 0.6, cy + rh * 1.1 ), ( cx, cy + rh * 1.55 ) ], ( 226, 220, 204 ) )
        c.poly( [ ( cx - rw * 0.42, cy + rh * 1.1 ), ( cx + rw * 0.42, cy + rh * 1.1 ), ( cx, cy + rh * 1.38 ) ], shade )
        c.ellipse( ( cx - rw * 1.05, cy - rh * 1.12, cx + rw * 1.05, cy + rh * 0.4 ), hair )
        face( c, cx, cy, rw, rh, -0.35, skin, shade, hair, lips=( 160, 58, 56 ) )
        c.poly( [ ( cx - rw * 0.95, cy - rh * 0.1 ), ( cx - rw * 0.2, cy - rh * 1.08 ), ( cx + rw * 0.8, cy - rh * 0.95 ), ( cx + rw * 0.95, cy - rh * 0.2 ),
                  ( cx + rw * 0.45, cy - rh * 0.7 ), ( cx - rw * 0.3, cy - rh * 0.72 ) ], hair )
        for s in ( -1, 1 ):
            bx = cx + s * rw * 0.8
            c.poly( [ ( bx - rw * 0.15, cy + rh * 0.5 ), ( bx + rw * 0.15, cy + rh * 0.5 ), ( bx + rw * 0.1, h * 0.84 ), ( bx - rw * 0.1, h * 0.84 ) ], hair )
            c.rect( ( bx - rw * 0.16, h * 0.8, bx + rw * 0.16, h * 0.83 ), ( 196, 40, 44 ) )
        base, wobble = 1.3, 0.8
    elif variant == "rostro_maestro":
        c = Canvas( w, h, ( 86, 110, 82 ) )
        c.rect( ( 0, h * 0.78, w, h ), ( 74, 56, 40 ) )
        cx, cy, rw, rh = w * 0.45, h * 0.34, w * 0.15, h * 0.13
        suit, shirt = ( 64, 46, 36 ), ( 228, 222, 206 )
        c.poly( [ ( w * 0.02, h ), ( w * 0.1, h * 0.58 ), ( cx - rw * 0.4, h * 0.5 ), ( cx + rw * 0.6, h * 0.5 ), ( w * 0.86, h * 0.6 ), ( w * 0.95, h ) ], suit )
        c.poly( [ ( cx - rw * 0.45, h * 0.5 ), ( cx + rw * 0.6, h * 0.5 ), ( cx + rw * 0.3, h * 0.66 ), ( cx - rw * 0.2, h * 0.66 ) ], shirt )
        c.poly( [ ( cx - rw * 0.15, h * 0.52 ), ( cx + rw * 0.35, h * 0.52 ), ( cx + rw * 0.1, h * 0.56 ) ], ( 20, 20, 22 ) )
        c.rect( ( cx - rw * 0.35, cy + rh * 0.6, cx + rw * 0.45, h * 0.51 ), shade )
        c.ellipse( ( cx - rw * 1.05, cy - rh * 1.1, cx + rw * 1.05, cy + rh * 0.3 ), ( 168, 164, 156 ) )
        face( c, cx, cy, rw, rh, 0.3, ( 178, 124, 94 ), ( 118, 76, 58 ), ( 70, 64, 60 ), old=True, mustache=True, glasses=True )
        c.poly( [ ( cx - rw * 1.0, cy - rh * 0.3 ), ( cx - rw * 0.7, cy - rh * 0.9 ), ( cx + rw * 0.1, cy - rh * 1.05 ), ( cx - rw * 0.4, cy - rh * 0.75 ) ],
                ( 186, 182, 174 ) )
        # The guitar across him: its body low right, the neck up to the left, his hand on the frets.
        gx, gy = w * 0.62, h * 0.82
        c.ellipse( ( gx - w * 0.26, gy - h * 0.12, gx + w * 0.06, gy + h * 0.16 ), ( 176, 112, 52 ) )
        c.ellipse( ( gx - w * 0.06, gy - h * 0.2, gx + w * 0.3, gy + h * 0.12 ), ( 176, 112, 52 ) )
        c.ellipse( ( gx - w * 0.05, gy - h * 0.06, gx + w * 0.03, gy + h * 0.02 ), ( 34, 24, 18 ) )
        c.poly( [ ( gx - w * 0.04, gy - h * 0.04 ), ( gx - w * 0.01, gy - h * 0.07 ), ( w * 0.08, h * 0.52 ), ( w * 0.04, h * 0.55 ) ], ( 70, 44, 26 ) )
        for j in range( 4 ):
            c.line( [ ( gx - w * ( 0.02 + 0.006 * j ), gy - h * 0.05 ), ( w * ( 0.05 + 0.006 * j ), h * 0.535 ) ], ( 220, 214, 200 ), 1, alpha=0.6 )
        c.ellipse( ( w * 0.07, h * 0.55, w * 0.17, h * 0.63 ), ( 178, 124, 94 ) )
        c.ellipse( ( gx + w * 0.02, gy - h * 0.04, gx + w * 0.13, gy + h * 0.05 ), ( 166, 114, 86 ) )
        base, wobble = 0.9, 0.9
    elif variant == "rostro_hermana":
        c = Canvas( w, h, ( 226, 206, 128 ) )
        for k in range( 9 ):
            x, y = rng.uniform( -0.1, 1.1 ) * w, rng.uniform( -0.1, 0.75 ) * h
            a, L, W = rng.uniform( 0, math.pi ), rng.uniform( 0.35, 0.55 ) * w, rng.uniform( 0.08, 0.13 ) * w
            ux, uy = math.cos( a ), math.sin( a )
            green = np.array( ( 52, 104, 58 ) ) * rng.uniform( 0.7, 1.25 )
            pts = [ ( x - ux * L / 2, y - uy * L / 2 ), ( x - uy * W + ux * L * 0.1, y + ux * W + uy * L * 0.1 ), ( x + ux * L / 2, y + uy * L / 2 ),
                    ( x + uy * W + ux * L * 0.1, y - ux * W + uy * L * 0.1 ) ]
            c.poly( pts, green )
            c.line( [ ( x - ux * L / 2, y - uy * L / 2 ), ( x + ux * L / 2, y + uy * L / 2 ) ], green * 0.7, 2.5 )
        cx, cy, rw, rh = w * 0.5, h * 0.4, w * 0.16, h * 0.14
        blouse = ( 236, 230, 216 )
        c.poly( [ ( w * 0.04, h ), ( w * 0.14, h * 0.66 ), ( w * 0.86, h * 0.66 ), ( w * 0.96, h ) ], blouse )
        c.rect( ( cx - rw * 0.42, cy + rh * 0.6, cx + rw * 0.42, h * 0.68 ), shade )
        c.poly( [ ( cx - rw * 0.9, h * 0.66 ), ( cx + rw * 0.9, h * 0.66 ), ( cx + rw * 0.9, h * 0.76 ), ( cx - rw * 0.9, h * 0.76 ) ], ( 236, 230, 216 ) )
        for j in range( 14 ):
            x = cx - rw * 0.85 + rw * 1.7 * j / 13
            col = ( ( 196, 40, 70 ), ( 232, 170, 40 ), ( 40, 120, 150 ), ( 60, 140, 60 ) )[j % 4]
            c.ellipse( ( x - w * 0.012, h * 0.7 - w * 0.012, x + w * 0.012, h * 0.7 + w * 0.012 ), col )
        c.ellipse( ( cx - rw * 1.08, cy - rh * 1.12, cx + rw * 1.08, cy + rh * 0.45 ), hair )
        c.ellipse( ( cx - rw * 0.6, cy - rh * 1.55, cx + rw * 0.6, cy - rh * 0.7 ), hair )
        face( c, cx, cy, rw, rh, 0.05, ( 192, 134, 100 ), ( 132, 86, 66 ), hair, lips=( 170, 60, 64 ) )
        c.poly( [ ( cx - rw * 1.0, cy - rh * 0.2 ), ( cx - rw * 0.4, cy - rh * 1.05 ), ( cx + rw * 0.4, cy - rh * 1.05 ), ( cx + rw * 1.0, cy - rh * 0.2 ),
                  ( cx + rw * 0.4, cy - rh * 0.75 ), ( cx - rw * 0.4, cy - rh * 0.75 ) ], hair )
        for j, ( fx, fy, col ) in enumerate( ( ( -0.75, -1.15, ( 206, 44, 60 ) ), ( -0.25, -1.45, ( 236, 176, 46 ) ), ( 0.3, -1.42, ( 196, 60, 140 ) ),
                                               ( 0.78, -1.1, ( 226, 90, 40 ) ) ) ):
            px_, py_ = cx + fx * rw, cy + fy * rh
            r = rw * 0.26
            for p in range( 6 ):
                a = 2 * math.pi * p / 6
                c.ellipse( ( px_ + math.cos( a ) * r * 0.6 - r * 0.45, py_ + math.sin( a ) * r * 0.6 - r * 0.45,
                             px_ + math.cos( a ) * r * 0.6 + r * 0.45, py_ + math.sin( a ) * r * 0.6 + r * 0.45 ), col )
            c.ellipse( ( px_ - r * 0.3, py_ - r * 0.3, px_ + r * 0.3, py_ + r * 0.3 ), ( 246, 222, 120 ) )
        for s in ( -1, 1 ):
            c.ellipse( ( cx + s * rw - w * 0.014, cy + rh * 0.3, cx + s * rw + w * 0.014, cy + rh * 0.46 ), ( 230, 186, 70 ) )
        base, wobble = 1.0, 1.0
    else:
        c = Canvas( w, h, ( 214, 172, 92 ) )
        horizon = h * 0.62
        c.rect( ( 0, horizon, w, h ), ( 168, 86, 52 ) )
        c.poly( [ ( 0, horizon ), ( w * 0.1, horizon - h * 0.05 ), ( w * 0.22, horizon - h * 0.05 ), ( w * 0.3, horizon ),
                  ( w * 0.7, horizon ), ( w * 0.76, horizon - h * 0.07 ), ( w * 0.92, horizon - h * 0.07 ), ( w, horizon ) ], ( 150, 96, 104 ) )
        cx, cy, rw, rh = w * 0.5, h * 0.42, w * 0.15, h * 0.13
        shirt = ( 230, 224, 206 )
        c.poly( [ ( w * 0.04, h ), ( w * 0.1, h * 0.62 ), ( cx - rw * 0.5, h * 0.585 ), ( cx + rw * 0.5, h * 0.585 ), ( w * 0.9, h * 0.62 ),
                  ( w * 0.96, h ) ], shirt )
        c.poly( [ ( w * 0.1, h * 0.62 ), ( w * 0.28, h * 0.6 ), ( w * 0.2, h ), ( w * 0.04, h ) ], ( 196, 190, 174 ) )
        c.rect( ( cx - rw * 0.48, cy + rh * 0.6, cx + rw * 0.48, h * 0.6 ), shade )
        c.poly( [ ( cx - rw * 0.95, h * 0.59 ), ( cx + rw * 0.95, h * 0.59 ), ( cx + rw * 0.1, h * 0.72 ) ], ( 178, 42, 40 ) )
        face( c, cx, cy, rw, rh, -0.1, ( 176, 118, 86 ), ( 116, 72, 54 ), hair, mustache=True, brim_shadow=0.15 )
        # The palm hat: its brim wide and pale, its crown a dome with a dark band.
        straw = ( 222, 196, 138 )
        c.ellipse( ( cx - rw * 2.7, cy - rh * 1.05, cx + rw * 2.7, cy - rh * 0.4 ), straw )
        c.ellipse( ( cx - rw * 2.7, cy - rh * 0.85, cx + rw * 2.7, cy - rh * 0.4 ), np.array( straw ) * 0.82 )
        c.poly( [ ( cx - rw * 1.0, cy - rh * 0.8 ), ( cx - rw * 0.85, cy - rh * 1.85 ), ( cx, cy - rh * 2.1 ), ( cx + rw * 0.85, cy - rh * 1.85 ),
                  ( cx + rw * 1.0, cy - rh * 0.8 ) ], straw )
        c.rect( ( cx - rw * 0.98, cy - rh * 1.0, cx + rw * 0.98, cy - rh * 0.82 ), ( 92, 52, 36 ) )
        for j in range( 9 ):
            x = cx - rw * 2.5 + rw * 5 * j / 8
            c.line( [ ( x, cy - rh * 0.95 ), ( cx + ( x - cx ) * 1.05, cy - rh * 0.45 ) ], np.array( straw ) * 0.78, 1.5, alpha=0.5 )
        base, wobble = 0.4, 0.8
    rgb = c.result()
    angle = stroke_angle( rng, h, w, base, wobble, 70, rgb, follow=0.8 )
    return paint( rgb, rng, angle, smear=2, dab_count=11000, dab_length=( 8.0, 20.0 ), dab_width=( 2.5, 5.5 ), dab_jitter=0.045 )


def sea( rng, w, h, variant=None ):
    """ A coast: a sky with clouds, the sea in horizontal strokes, foam, sometimes the sun on the water, rocks or a
    sail. """
    sunset = variant in ( "marea_violeta", "marea_ola" )
    if sunset:
        top, horizon_sky = ( 64, 58, 120 ), ( 238, 150, 98 )
        sea_far, sea_near = ( 92, 70, 120 ), ( 36, 40, 74 )
    else:
        top, horizon_sky = ( 54, 112, 178 ), ( 214, 222, 220 )
        sea_far, sea_near = ( 46, 104, 140 ), ( 18, 56, 82 )
    c = Canvas( w, h, top )
    horizon = h * ( 0.36 if variant == "marea_ola" else rng.uniform( 0.4, 0.55 ) )
    ys = np.linspace( 0, 1, h * c.k, dtype=np.float32 )[:, None, None]
    sky_t = np.clip( ys / ( horizon / h ), 0, 1 ) ** 1.4
    sky = srgb( top ) * ( 1 - sky_t ) + srgb( horizon_sky ) * sky_t
    sea_t = np.clip( ( ys - horizon / h ) / ( 1 - horizon / h ), 0, 1 ) ** 0.8
    water = srgb( sea_far ) * ( 1 - sea_t ) + srgb( sea_near ) * sea_t
    c.rgb = np.where( ys < horizon / h, sky, water ) * np.ones( ( 1, w * c.k, 1 ), np.float32 )
    # Clouds: banks of soft blobs, lit from above and shaded under.
    n = field( rng, h * c.k, w * c.k, 70, 2.0 ) + 0.6 * field( rng, h * c.k, w * c.k, 25, 1.5 )
    band = np.exp( -( ( ys[..., 0] - horizon / h * rng.uniform( 0.35, 0.7 ) ) / 0.14 ) ** 2 )
    cloud = np.clip( ( n * 0.5 + band * 1.4 - 0.9 ) * 1.6, 0, 1 ) * np.clip( 1 - ys[..., 0] / ( horizon / h * 0.97 ), 0, 1 )
    cloud = gaussian_filter( cloud, 2 )
    lit = np.clip( cloud - np.roll( cloud, 14, 0 ), 0, 1 )
    cloud_colour = srgb( ( 252, 226, 200 ) if sunset else ( 246, 246, 242 ) )
    shade_colour = srgb( ( 150, 110, 140 ) if sunset else ( 168, 182, 196 ) )
    body = cloud_colour * lit[..., None] * 1.0 + shade_colour * ( cloud - lit )[..., None]
    c.rgb = c.rgb * ( 1 - cloud[..., None] * 0.9 ) + body * 0.9
    if variant != "marea_punta":
        sx = w * rng.uniform( 0.3, 0.7 )
        sy = horizon - h * rng.uniform( 0.04, 0.12 )
        r = w * 0.045
        c.ellipse( ( sx - r * 3, sy - r * 3, sx + r * 3, sy + r * 3 ), ( 250, 210, 150 ), 0.3, blur=14 )
        c.ellipse( ( sx - r, sy - r, sx + r, sy + r ), ( 255, 236, 190 ) )
        for k in range( 46 ):
            y = horizon + ( h - horizon ) * ( k / 46 ) ** 1.6
            half = w * ( 0.012 + 0.09 * k / 46 ) * rng.uniform( 0.3, 1.0 )
            c.line( [ ( sx - half, y ), ( sx + half, y ) ], ( 252, 214, 160 ), 2 + 4 * k / 46, alpha=0.7 )
    for k in range( 160 ):
        t = rng.random() ** 1.6
        y = horizon + ( h - horizon ) * t
        L = w * ( 0.02 + 0.17 * t ) * rng.uniform( 0.5, 1.2 )
        x = rng.uniform( -0.1, 1.0 ) * w
        dark = np.array( sea_near ) * 0.7
        c.line( [ ( x, y ), ( x + L * 0.5, y - 2 - 3 * t ), ( x + L, y ) ], dark, 1.5 + 5 * t, alpha=0.55 )
        if rng.random() < 0.5:
            c.line( [ ( x + L * 0.2, y - 3 - 4 * t ), ( x + L * 0.6, y - 4 - 5 * t ) ], ( 236, 240, 236 ), 1 + 3 * t, alpha=0.75 )
    if variant == "marea_ola":
        # A breaking wave across the front: its dark face, the curl, the foam.
        crest = [ ( x, h * 0.62 - h * 0.18 * math.exp( -( ( x / w - 0.62 ) / 0.22 ) ** 2 ) ) for x in np.linspace( -10, w + 10, 60 ) ]
        c.poly( crest + [ ( w + 10, h ), ( -10, h ) ], ( 26, 70, 92 ) )
        c.poly( crest + [ ( x, y + h * 0.05 ) for x, y in reversed( crest ) ], ( 60, 140, 150 ), alpha=0.8 )
        c.line( crest, ( 240, 244, 240 ), 7, alpha=0.9 )
        for k in range( 50 ):
            x = rng.uniform( 0.35, 0.9 ) * w
            y = h * 0.6 - h * 0.18 * math.exp( -( ( x / w - 0.62 ) / 0.22 ) ** 2 ) + rng.uniform( -6, 14 )
            r = rng.uniform( 2, 9 )
            c.ellipse( ( x - r, y - r, x + r, y + r ), ( 244, 246, 242 ), 0.85 )
    elif variant in ( "marea_punta", "marea_barcas" ):
        side = -1 if variant == "marea_punta" else 1
        x0 = w * ( 0.0 if side < 0 else 0.62 )
        x1 = w * ( 0.4 if side < 0 else 1.0 )
        pts = [ ( x0, horizon + h * 0.08 ) ]
        for k in range( 11 ):
            pts.append( ( x0 + ( x1 - x0 ) * k / 10, horizon - h * rng.uniform( 0.03, 0.2 ) * ( 1 - abs( k / 10 - ( 0.25 if side < 0 else 0.75 ) ) ) ) )
        pts.append( ( x1, horizon + h * 0.08 ) )
        rock = ( 70, 48, 58 ) if sunset else ( 98, 88, 74 )
        c.poly( pts, rock )
        c.poly( [ ( p[0], p[1] + h * 0.015 ) for p in pts[1:-1] ] + [ ( x1, horizon + h * 0.08 ), ( x0, horizon + h * 0.08 ) ], np.array( rock ) * 0.7, alpha=0.6 )
        c.line( [ ( x0, horizon + h * 0.07 ), ( x1, horizon + h * 0.07 ) ], ( 240, 240, 236 ), 6, alpha=0.7, blur=1.5 )
    if variant in ( "marea_barcas", "marea_violeta" ):
        for k in range( 3 if variant == "marea_barcas" else 1 ):
            bx, by = w * rng.uniform( 0.15, 0.6 ), horizon + h * rng.uniform( 0.04, 0.2 )
            s = h * rng.uniform( 0.06, 0.11 )
            c.poly( [ ( bx, by - s ), ( bx + s * 0.55, by ), ( bx, by ) ], ( 240, 232, 216 ) )
            c.poly( [ ( bx, by - s * 0.8 ), ( bx - s * 0.35, by ), ( bx, by ) ], ( 222, 210, 190 ) )
            c.poly( [ ( bx - s * 0.4, by ), ( bx + s * 0.65, by ), ( bx + s * 0.5, by + s * 0.14 ), ( bx - s * 0.28, by + s * 0.14 ) ], ( 58, 40, 36 ) )
    rgb = c.result()
    ys = np.linspace( 0, 1, h, dtype=np.float32 )[:, None]
    angle = stroke_angle( rng, h, w, 0.0, 0.2, 90, rgb, follow=0.5 )
    sky_angle = stroke_angle( rng, h, w, 0.5, 0.9, 60 )
    angle = np.where( ys < horizon / h, sky_angle, angle ).astype( np.float32 )
    return paint( rgb, rng, angle, smear=2, stroke=16, dab_count=12000, dab_length=( 10.0, 26.0 ), dab_width=( 2.5, 6.0 ), dab_jitter=0.05 )


def plateau( rng, w, h, variant=None ):
    """ The plateau: mesas in layers of red and mauve under a pale sky, red earth, agaves and a prickly pear. """
    dusk = variant in ( "tierra_magueyes", "tierra_camino" )
    c = Canvas( w, h, ( 228, 216, 186 ) )
    horizon = h * ( 0.62 if variant == "tierra_magueyes" else rng.uniform( 0.44, 0.56 ) )
    ys = np.linspace( 0, 1, h * c.k, dtype=np.float32 )[:, None, None]
    top, low = ( ( 92, 70, 118 ), ( 240, 156, 92 ) ) if dusk else ( ( 120, 170, 196 ), ( 238, 226, 196 ) )
    t = np.clip( ys / ( horizon / h ), 0, 1 )
    c.rgb = ( srgb( top ) * ( 1 - t ) + srgb( low ) * t ) * np.ones( ( 1, w * c.k, 1 ), np.float32 )
    n = field( rng, h * c.k, w * c.k, 60, 2.0 )
    cloud = np.clip( ( n - 0.9 ) * 1.2, 0, 1 ) * np.clip( 1 - ys[..., 0] / ( horizon / h * 0.8 ), 0, 1 )
    c.rgb = c.rgb * ( 1 - cloud[..., None] * 0.6 ) + srgb( ( 250, 236, 214 ) ) * cloud[..., None] * 0.6
    if variant != "tierra_roja":
        sx, sy, r = w * rng.uniform( 0.2, 0.8 ), horizon - h * rng.uniform( 0.16, 0.28 ), w * rng.uniform( 0.05, 0.075 )
        c.ellipse( ( sx - r * 2.4, sy - r * 2.4, sx + r * 2.4, sy + r * 2.4 ), ( 252, 220, 160 ), 0.25, blur=12 )
        c.ellipse( ( sx - r, sy - r, sx + r, sy + r ), ( 252, 232, 170 ) if not dusk else ( 250, 196, 120 ) )
    layers = [ ( ( 168, 128, 150 ), 0.10 ), ( ( 186, 96, 72 ), 0.16 ), ( ( 150, 60, 44 ), 0.08 ) ]
    if dusk:
        layers = [ ( ( 120, 82, 120 ), 0.1 ), ( ( 146, 66, 70 ), 0.15 ), ( ( 104, 44, 46 ), 0.08 ) ]
    for depth, ( colour, height ) in enumerate( layers ):
        x = -w * 0.1
        pts = [ ( x, horizon + h * 0.02 ) ]
        while x < w * 1.1:
            span = w * rng.uniform( 0.12, 0.35 )
            top_y = horizon - h * height * rng.uniform( 0.4, 1.2 )
            if rng.random() < 0.55:
                pts += [ ( x + span * 0.1, top_y + h * 0.01 ), ( x + span * 0.14, top_y ), ( x + span * 0.84, top_y ), ( x + span * 0.88, top_y + h * 0.012 ) ]
            else:
                pts += [ ( x + span * 0.5, horizon - h * height * 0.2 ) ]
            x += span
            pts.append( ( x, horizon - h * height * rng.uniform( 0.0, 0.25 ) ) )
        pts.append( ( w * 1.1, horizon + h * 0.02 ) )
        c.poly( pts, colour )
        # The cliffs' shaded faces and strata.
        lit = np.array( colour ) * 1.12
        for k in range( 4 ):
            y = horizon - h * height * ( 0.2 + 0.18 * k )
            c.line( [ ( 0, y ), ( w * 0.5, y + h * 0.003 ), ( w, y - h * 0.002 ) ], np.array( colour ) * 0.82, 2.0, alpha=0.3 )
        c.poly( [ ( p[0] + w * 0.012, p[1] ) for p in pts ], lit, alpha=0.18 )
    t = np.clip( ( ys - horizon / h ) / ( 1 - horizon / h ), 0, 1 )
    earth = srgb( ( 196, 92, 52 ) if not dusk else ( 150, 64, 46 ) ) * ( 1 - t ) + srgb( ( 222, 140, 72 ) if not dusk else ( 186, 96, 60 ) ) * t
    below = ( ys >= ( horizon + h * 0.02 ) / h ).astype( np.float32 )
    c.rgb = c.rgb * ( 1 - below ) + earth * below
    furrows = field( rng, h * c.k, w * c.k, 18, 1.0 ) * below[..., 0]
    c.rgb *= ( 1 + 0.05 * furrows[..., None] )
    if variant in ( "tierra_camino", "tierra_mesa" ):
        c.poly( [ ( w * 0.49, horizon + h * 0.03 ), ( w * 0.52, horizon + h * 0.03 ), ( w * 0.74, h ), ( w * 0.38, h ) ], ( 230, 176, 110 ), alpha=0.65 )
    for k in range( 6 if variant == "tierra_magueyes" else int( rng.integers( 2, 5 ) ) ):
        big = variant == "tierra_magueyes" and k < 2
        ax = w * ( ( 0.3, 0.72 )[k] if big else rng.uniform( 0.05, 0.95 ) )
        ay = h * ( 0.96 if big else rng.uniform( 0.76, 0.97 ) )
        size = h * ( rng.uniform( 0.3, 0.38 ) if big else rng.uniform( 0.08, 0.2 ) )
        leaf = np.array( ( 84, 118, 110 ) if not dusk else ( 62, 90, 92 ) )
        for j in range( 13 ):
            a = math.pi * ( 0.06 + 0.88 * j / 12 ) + rng.uniform( -0.07, 0.07 )
            L = size * rng.uniform( 0.62, 1.0 ) * ( 1 - 0.3 * abs( j / 12 - 0.5 ) )
            tip = ( ax - math.cos( a ) * L, ay - math.sin( a ) * L )
            base_w = size * 0.075
            pts = [ ( ax - math.sin( a ) * base_w, ay + math.cos( a ) * base_w * 0.3 ), tip, ( ax + math.sin( a ) * base_w, ay - math.cos( a ) * base_w * 0.3 ) ]
            shade_ = rng.uniform( 0.75, 1.2 )
            c.poly( pts, leaf * shade_ )
            c.line( [ ( ax, ay ), tip ], leaf * shade_ * 1.25, max( 1.0, size * 0.01 ), alpha=0.5 )
    if variant in ( "tierra_roja", "tierra_magueyes" ):
        px, py = w * rng.uniform( 0.15, 0.85 ), h * rng.uniform( 0.84, 0.95 )
        s = h * 0.07
        for dx, dy in ( ( 0, 0 ), ( -0.8, -1.2 ), ( 0.8, -1.3 ), ( 0.1, -2.3 ) ):
            x, y = px + dx * s, py + dy * s
            c.ellipse( ( x - s * 0.6, y - s * 0.9, x + s * 0.6, y + s * 0.9 ), ( 96, 128, 70 ) if not dusk else ( 70, 92, 60 ) )
            c.ellipse( ( x - s * 0.4, y - s * 0.75, x + s * 0.1, y + s * 0.4 ), ( 126, 156, 90 ), 0.4, blur=2 )
    rgb = c.result()
    ys = np.linspace( 0, 1, h, dtype=np.float32 )[:, None]
    angle = stroke_angle( rng, h, w, 0.05, 0.3, 70, rgb, follow=0.6 )
    sky_angle = stroke_angle( rng, h, w, 0.3, 0.8, 60 )
    angle = np.where( ys < horizon / h - 0.05, sky_angle, angle ).astype( np.float32 )
    return paint( rgb, rng, angle, smear=2, dab_count=11000, dab_length=( 9.0, 24.0 ), dab_width=( 2.5, 6.0 ), dab_jitter=0.055 )


def drawing( rng, w, h, variant=None ):
    """ A sculptor's charcoal study on cream paper under a white mat, in a few long searching lines, hatched on the
    shaded side and smudged: for «Vacío» a reclining figure in four masses (the head, the shoulders, the hips, the
    raised knees) pierced twice, after the reclining figures of the mid-century; for the torso a standing torso blocked
    out in its planes. A small second study, notes and the artist's initials. """
    mat = 0.12
    paper = np.ones( ( h, w, 3 ), np.float32 ) * srgb( ( 236, 229, 212 ) )
    fibres = gaussian_filter( rng.standard_normal( ( h, w ) ).astype( np.float32 ), ( 0.6, 2.5 ) )
    paper *= ( 1 + 0.02 * fibres[..., None] )
    K = 2
    line_layer = Image.new( "L", ( w * K, h * K ), 0 )
    d = ImageDraw.Draw( line_layer )
    fill_layer = Image.new( "L", ( w * K, h * K ), 0 )
    f = ImageDraw.Draw( fill_layer )
    hatch = Image.new( "L", ( w * K, h * K ), 0 )
    hd = ImageDraw.Draw( hatch )

    def curve( points, width, value ):
        d.line( [ ( x * K, y * K ) for x, y in points ], fill=value, width=max( 1, int( width * K ) ), joint="curve" )

    torso = variant == "forma_torso"
    cx, cy = w * 0.5, h * ( 0.46 if torso else 0.5 )
    R = min( w, h ) * ( 0.25 if torso else 0.26 )

    def ellipse_points( ex, ey, rx, ry, turn, wobble=0.0, count=60, a0=0.0, a1=2 * math.pi ):
        pts = []
        c, s = math.cos( turn ), math.sin( turn )
        for j in range( count + 1 ):
            a = a0 + ( a1 - a0 ) * j / count
            r = 1 + wobble * math.sin( 3 * a + ex * 7 ) + 0.5 * wobble * math.sin( 5 * a + ey * 5 )
            x, y = rx * math.cos( a ) * r, ry * math.sin( a ) * r
            pts.append( ( cx + R * ( ex + x * c - y * s ), cy + R * ( ey + x * s + y * c ) ) )
        return pts

    def chaikin( pts, rounds=3 ):
        for _ in range( rounds ):
            out = []
            for a, b in zip( pts, pts[1:] + pts[:1] ):
                out += [ ( a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25 ), ( a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75 ) ]
            pts = out
        return pts

    if torso:
        # A standing torso blocked out: the neck's stump, the shoulders and the arms cut off, the waist, the hips and the
        # thighs' stumps, then its planes: the chest, the breastbone, the ribs' arch, the navel, the groin.
        half = [ ( 0.17, -1.28 ), ( 0.2, -1.14 ), ( 0.6, -1.06 ), ( 0.74, -0.86 ), ( 0.64, -0.52 ), ( 0.52, -0.2 ), ( 0.44, 0.12 ),
                 ( 0.56, 0.48 ), ( 0.6, 0.86 ), ( 0.42, 1.08 ), ( 0.06, 0.98 ) ]
        silhouette = [ ( x, y ) for x, y in half ] + [ ( -x, y ) for x, y in reversed( half ) ]
        outline = [ ( cx + R * x, cy + R * y ) for x, y in chaikin( silhouette ) ]
        f.polygon( [ ( x * K, y * K ) for x, y in outline ], fill=255 )
        for k in range( 3 ):
            start = int( rng.integers( 0, len( outline ) ) )
            part = ( outline + outline )[start:start + int( len( outline ) * rng.uniform( 0.6, 1.0 ) )]
            curve( [ ( x + rng.normal( 0, 1.0 ), y + rng.normal( 0, 1.0 ) ) for x, y in part ], rng.uniform( 1.1, 2.6 ), int( rng.uniform( 140, 235 ) ) )
        planes = [
            [ ( -0.5, -0.86 ), ( -0.25, -0.6 ), ( -0.02, -0.66 ) ], [ ( 0.5, -0.86 ), ( 0.25, -0.6 ), ( 0.02, -0.66 ) ],
            [ ( 0.0, -1.1 ), ( 0.0, -0.5 ) ], [ ( -0.42, -0.42 ), ( 0.0, -0.18 ), ( 0.42, -0.42 ) ],
            [ ( -0.3, 0.55 ), ( 0.0, 0.88 ), ( 0.3, 0.55 ) ], [ ( -0.38, -0.05 ), ( -0.3, 0.3 ) ], [ ( 0.38, -0.05 ), ( 0.3, 0.3 ) ] ]
        for line in planes:
            pts = [ ( cx + R * x + rng.normal( 0, 0.6 ), cy + R * y + rng.normal( 0, 0.6 ) ) for x, y in line ]
            curve( pts, 1.0, int( rng.uniform( 100, 170 ) ) )
        d.ellipse( ( ( cx - R * 0.04 ) * K, ( cy + R * 0.12 ) * K, ( cx + R * 0.04 ) * K, ( cy + R * 0.2 ) * K ), outline=180, width=K )
        for j in range( 150 ):
            x = cx + R * rng.uniform( 0.05, 0.7 )
            y = cy + R * rng.uniform( -1.1, 1.0 )
            L = R * rng.uniform( 0.06, 0.14 )
            hd.line( [ ( x * K, y * K ), ( ( x + L * 0.5 ) * K, ( y - L ) * K ) ], fill=int( rng.uniform( 90, 200 ) ), width=K )
        holes = []
    else:
        # A reclining figure in four masses: the head, the shoulders (pierced), the hips, the raised knees (pierced).
        lobes = [ ( -1.02, -0.44, 0.22, 0.27, -0.35 ), ( -0.52, -0.08, 0.58, 0.42, -0.45 ), ( 0.22, 0.3, 0.52, 0.36, 0.15 ),
                  ( 0.86, -0.08, 0.42, 0.52, 0.6 ) ]
        holes = [ ( -0.46, -0.04, 0.14, 0.17 ), ( 0.78, 0.12, 0.13, 0.22 ) ]

        def inside( x, y, skip ):
            for k, ( ex, ey, rx, ry, turn ) in enumerate( lobes ):
                if k == skip:
                    continue
                c, s = math.cos( -turn ), math.sin( -turn )
                px, py = ( x - cx ) / R - ex, ( y - cy ) / R - ey
                lx, ly = px * c - py * s, px * s + py * c
                if ( lx / ( rx * 0.94 ) ) ** 2 + ( ly / ( ry * 0.94 ) ) ** 2 < 1:
                    return True
            return False

        for ex, ey, rx, ry, turn in lobes:
            f.polygon( [ ( x * K, y * K ) for x, y in ellipse_points( ex, ey, rx, ry, turn, 0.04 ) ], fill=255 )
        for ex, ey, rx, ry in holes:
            f.polygon( [ ( x * K, y * K ) for x, y in ellipse_points( ex, ey, rx, ry, 0.0 ) ], fill=0 )
        # The masses' edges where they're the figure's outline (not where one runs into the next), traced a few times.
        for index, ( ex, ey, rx, ry, turn ) in enumerate( lobes ):
            for k in range( int( rng.integers( 2, 4 ) ) ):
                pts = ellipse_points( ex, ey, rx * rng.uniform( 0.98, 1.02 ), ry * rng.uniform( 0.98, 1.02 ), turn, 0.05, 90 )
                run = []
                for x, y in pts:
                    if inside( x, y, index ):
                        if len( run ) > 2:
                            curve( [ ( a + rng.normal( 0, 0.9 ), b + rng.normal( 0, 0.9 ) ) for a, b in run ], rng.uniform( 1.0, 2.6 ), int( rng.uniform( 130, 235 ) ) )
                        run = []
                    else:
                        run.append( ( x, y ) )
                if len( run ) > 2:
                    curve( [ ( a + rng.normal( 0, 0.9 ), b + rng.normal( 0, 0.9 ) ) for a, b in run ], rng.uniform( 1.0, 2.6 ), int( rng.uniform( 130, 235 ) ) )
            # A cross-contour over the mass, following its swell, and hatching on its shaded side.
            pts = ellipse_points( ex, ey + ry * 0.15, rx * 0.9, ry * 0.2, turn, 0.0, 30, math.pi * 0.08, math.pi * 0.92 )
            curve( pts, 0.8, 95 )
            c, s = math.cos( turn ), math.sin( turn )
            for j in range( 46 ):
                u, v = rng.uniform( -0.2, 1.0 ), rng.uniform( -0.1, 1.0 )
                x = cx + R * ( ex + ( u * rx ) * c - ( v * ry ) * s )
                y = cy + R * ( ey + ( u * rx ) * s + ( v * ry ) * c )
                L = R * rng.uniform( 0.06, 0.13 )
                hd.line( [ ( x * K, y * K ), ( ( x + L * 0.5 ) * K, ( y - L ) * K ) ], fill=int( rng.uniform( 90, 200 ) ), width=K )
    for ex, ey, rx, ry in holes:
        for k in range( 2 ):
            pts = [ ( x + rng.normal( 0, 0.7 ), y + rng.normal( 0, 0.7 ) ) for x, y in ellipse_points( ex, ey, rx, ry, 0.0, 0.03, 40 ) ]
            curve( pts, 1.7, 215 )
        # The inside of the hole, in shadow.
        for j in range( 14 ):
            a = rng.uniform( 0.2, 1.3 ) * math.pi
            x = cx + R * ( ex + rx * 0.85 * math.cos( a ) )
            y = cy + R * ( ey + ry * 0.85 * math.sin( a ) )
            hd.line( [ ( x * K, y * K ), ( ( x + R * 0.05 ) * K, ( y - R * 0.08 ) * K ) ], fill=210, width=K )
    clip = np.asarray( fill_layer, np.float32 ) / 255.0
    hatch_a = np.asarray( hatch, np.float32 ) / 255.0
    # Hatching stays inside the masses, but the holes' shading is drawn in them.
    hole_mask = Image.new( "L", ( w * K, h * K ), 0 )
    hm = ImageDraw.Draw( hole_mask )
    for ex, ey, rx, ry in holes:
        hm.polygon( [ ( x * K, y * K ) for x, y in ellipse_points( ex, ey, rx * 1.05, ry * 1.05, 0.0 ) ], fill=255 )
    hatch_a = hatch_a * np.clip( clip + np.asarray( hole_mask, np.float32 ) / 255.0, 0, 1 )
    # The ground line under it, a small second study, notes and initials.
    ground = cy + R * ( 1.15 if torso else 0.72 )
    curve( [ ( w * 0.16, ground + rng.normal( 0, 1 ) ), ( w * 0.5, ground + rng.normal( 0, 1 ) ), ( w * 0.84, ground + rng.normal( 0, 1 ) ) ], 1.2, 140 )
    sx, sy, sr = w * 0.24, h * 0.8, R * 0.28
    for k in range( 2 ):
        curve( [ ( sx + sr * math.cos( 2 * math.pi * j / 30 ) * 0.75 + rng.normal( 0, 0.6 ), sy + sr * math.sin( 2 * math.pi * j / 30 ) + rng.normal( 0, 0.6 ) )
                 for j in range( 31 ) ], 1.0, 150 )
    for j in range( 3 ):
        y = h * ( 0.2 + 0.028 * j )
        x0 = w * 0.6
        pts = [ ( x0 + s * 3.0, y + 2.0 * math.sin( s * 1.3 + j ) ) for s in range( int( rng.integers( 18, 34 ) ) ) ]
        curve( pts, 0.8, 120 )
    d.text( ( w * K * 0.84, h * K * 0.85 ), "L.G." if not torso else "M.E.", font=font( "Dinish-Italic.ttf", int( h * 0.045 ) ), fill=170, anchor="mm" )
    lines = np.asarray( line_layer, np.float32 ) / 255.0
    ink = np.clip( lines + hatch_a * 0.8, 0, 1 )
    ink = np.asarray( Image.fromarray( np.uint8( ink * 255 ) ).resize( ( w, h ), Image.LANCZOS ), np.float32 ) / 255.0
    clip = np.asarray( Image.fromarray( np.uint8( clip * 255 ) ).resize( ( w, h ), Image.LANCZOS ), np.float32 ) / 255.0
    tone = gaussian_filter( clip, 12 ) * 0.16 * ( 0.6 + 0.4 * field( rng, h, w, 50 ) )
    smudge = gaussian_filter( ink, 6 ) * 0.32
    charcoal = np.clip( ink + smudge + tone, 0, 1 )
    grain = np.clip( 1 + 0.4 * rng.standard_normal( ( h, w ) ).astype( np.float32 ), 0.3, 1.7 )
    charcoal = np.clip( charcoal * grain, 0, 1 )
    art = paper * ( 1 - charcoal[..., None] * 0.86 ) + srgb( ( 34, 32, 34 ) ) * charcoal[..., None] * 0.86
    out = np.ones( ( h, w, 3 ), np.float32 ) * srgb( ( 244, 242, 236 ) )
    mx, my = int( w * mat ), int( h * mat )
    out[my:h - my, mx:w - mx] = art[my:h - my, mx:w - mx]
    out[my - 3:my, mx - 3:w - mx + 3] = srgb( ( 252, 250, 246 ) )
    out[my - 3:h - my + 3, mx - 3:mx] = srgb( ( 252, 250, 246 ) )
    out[h - my:h - my + 3, mx - 3:w - mx + 3] = srgb( ( 214, 210, 202 ) )
    out[my - 3:h - my + 3, w - mx:w - mx + 3] = srgb( ( 214, 210, 202 ) )
    height = np.zeros( ( h, w ), np.float32 )
    height[my:h - my, mx:w - mx] = -2.0 + 0.3 * fibres[my:h - my, mx:w - mx]
    height = gaussian_filter( height, 0.8 )
    rough = np.where( height < -0.5, 0.86, 0.9 ).astype( np.float32 )
    return out, height, rough


def colour_field( rng, w, h, variant=None ):
    """ Colour-field painting: two or three soft-edged blocks stacked on a ground, their edges feathered and brushed. """
    palettes = {
        "campo_4": ( ( 138, 36, 34 ), [ ( 214, 92, 40 ), ( 92, 22, 26 ), ( 236, 172, 60 ) ] ),
        "campo_7": ( ( 28, 54, 70 ), [ ( 58, 120, 128 ), ( 204, 190, 150 ), ( 16, 30, 40 ) ] ),
    }
    ground, blocks = palettes.get( variant, palettes["campo_4"] )
    c = Canvas( w, h, ground, k=1 )
    count = len( blocks )
    margin = w * 0.07
    gap = h * 0.04
    span = ( h - 2 * margin - gap * ( count - 1 ) )
    weights = rng.uniform( 0.7, 1.4, count )
    weights /= weights.sum()
    y = margin
    for colour, wt in zip( blocks, weights ):
        hh = span * wt
        m = c.mask( lambda d, k, y=y, hh=hh: d.rectangle( ( margin, y, w - margin, y + hh ), fill=255 ) )
        edge = field( rng, h, w, 30 )
        m = np.clip( gaussian_filter( m, 9 ) + 0.12 * edge * gaussian_filter( m, 18 ) * ( 1 - m ), 0, 1 )
        inner = srgb( colour )[None, None, :] * ( 1 + 0.07 * field( rng, h, w, 120 )[..., None] )
        c.rgb = c.rgb * ( 1 - m[..., None] ) + inner * m[..., None]
        y += hh + gap
    rgb = c.rgb
    angle = stroke_angle( rng, h, w, 0.0, 0.5, 120 )
    return paint( rgb, rng, angle, smear=3, stroke=20, streak=0.03, impasto=0.6, dab_count=9000, dab_length=( 16.0, 40.0 ),
                  dab_width=( 5.0, 11.0 ), dab_jitter=0.03 )


GENERATORS = { "portrait": portrait, "sea": sea, "plateau": plateau, "drawing": drawing, "field": colour_field }


# ---------------------------------------------------------------------------------------------------------------------
# The art atlas

def work_size( aspect ):
    return ( WORK, int( round( WORK / aspect ) ) ) if aspect >= 1 else ( int( round( WORK * aspect ) ), WORK )


def build_art( out_dir ):
    size = CELL * 4
    colour = np.zeros( ( size, size, 3 ), np.float32 )
    height = np.zeros( ( size, size ), np.float32 )
    rough = np.zeros( ( size, size ), np.float32 )
    layout = {}
    for index, ( key, show, artist, title, year, technique, aspect, kind, seed ) in enumerate( WORKS ):
        rng = np.random.default_rng( seed )
        w, h = work_size( aspect )
        rgb, hgt, rgh = GENERATORS[kind]( rng, w, h, key )
        cx, cy = ( index % 4 ) * CELL, ( index // 4 ) * CELL
        ox, oy = ( CELL - w ) // 2, ( CELL - h ) // 2
        pad = ( ( oy, CELL - h - oy ), ( ox, CELL - w - ox ) )
        colour[cy:cy + CELL, cx:cx + CELL] = np.pad( rgb, pad + ( ( 0, 0 ), ), mode="edge" )
        height[cy:cy + CELL, cx:cx + CELL] = np.pad( hgt, pad, mode="edge" )
        rough[cy:cy + CELL, cx:cx + CELL] = np.pad( rgh, pad, mode="edge" )
        # UVs with v up the picture (map_kit's): the work's corners in the sheet, half a pixel in.
        u0, u1 = ( cx + ox + 0.5 ) / size, ( cx + ox + w - 0.5 ) / size
        v0, v1 = 1 - ( cy + oy + h - 0.5 ) / size, 1 - ( cy + oy + 0.5 ) / size
        name, life = ARTISTS[artist]
        layout[key] = { "uv": [ u0, v0, u1, v1 ], "aspect": w / h, "show": show, "kind": kind, "artist": name,
                        "life": life, "title": title, "year": year, "technique": technique, "label": index }
        print( f"  {key}: {kind} {w}x{h}", flush=True )
    save_png( out_dir / "art_color.png", colour )
    half = height.reshape( size // 2, 2, size // 2, 2 ).mean( axis=( 1, 3 ) )
    save_png( out_dir / "art_normal.png", gl_normal( half, 0.9 ) )
    save_png( out_dir / "art_rough.png", rough.reshape( size // 2, 2, size // 2, 2 ).mean( axis=( 1, 3 ) ), "L" )
    write_text( out_dir / "cb_art.vmat", vmat_text( {
        "TextureColor": f"{RESOURCE}/art_color.png", "TextureNormal": f"{RESOURCE}/art_normal.png",
        "TextureRoughness": f"{RESOURCE}/art_rough.png", "TextureAmbientOcclusion": "materials/default/default_ao.tga" } ) )
    return layout


# ---------------------------------------------------------------------------------------------------------------------
# Wall texts, labels and signs

def vmat_text( textures, extra=None, metal=0.0 ):
    lines = [ "// Tools/cerroblanco_art.py", '"Layer0"', "{", '    shader "shaders/complex.shader"', '    F_SPECULAR "1"' ]
    for key, value in ( extra or {} ).items():
        lines.append( f'    {key} "{value}"' )
    lines += [ f'    g_flMetalness "{metal}"', '    g_flRoughnessScaleFactor "1"', '    g_flModelTintAmount "1"',
               '    g_vColorTint "[1 1 1 1]"' ]
    lines += [ f'    {key} "{value}"' for key, value in textures.items() ]
    return "\n".join( lines + [ "}" ] ) + "\n"


def wrap( text, face, width ):
    words, lines, line = text.split(), [], ""
    for word in words:
        trial = f"{line} {word}".strip()
        if face.getlength( trial ) <= width:
            line = trial
        else:
            lines.append( line )
            line = word
    return lines + [ line ] if line else lines


def build_walltext( out_dir ):
    """ Each show's wall text in a 2048 x 512 band: the title, the subtitle, a rule and the introduction. """
    W, H = 2048, 2048
    alpha = Image.new( "L", ( W, H ), 0 )
    d = ImageDraw.Draw( alpha )
    layout = {}
    for k, ( key, ( title, subtitle, text, where ) ) in enumerate( SHOWS.items() ):
        y0 = k * 512
        size = 150
        while font( "Mina-Bold.ttf", size ).getlength( title ) > 1180:
            size -= 4
        d.text( ( 40, y0 + 30 ), title, font=font( "Mina-Bold.ttf", size ), fill=255, anchor="la" )
        d.text( ( 44, y0 + 210 ), subtitle, font=font( "Dinish-Regular.ttf", 58 ), fill=255, anchor="la" )
        d.rectangle( ( 44, y0 + 292, 1180, y0 + 296 ), fill=255 )
        body = font( "Dinish-Regular.ttf", 30 )
        for j, line in enumerate( wrap( text, body, 1130 ) ):
            d.text( ( 44, y0 + 318 + j * 38 ), line, font=body, fill=255, anchor="la" )
        # The right-hand column: where, the credit.
        small = font( "Dinish-Regular.ttf", 28 )
        d.text( ( 1300, y0 + 60 ), where.upper(), font=font( "Dinish-Bold.ttf", 40 ), fill=255, anchor="la" )
        for j, line in enumerate( wrap( CREDIT, small, 680 ) ):
            d.text( ( 1300, y0 + 330 + j * 36 ), line, font=small, fill=255, anchor="la" )
        layout[key] = { "title": [ 0, 1 - ( y0 + 504 ) / H, 1200 / W, 1 - y0 / H ], "credit": [ 1290 / W, 1 - ( y0 + 504 ) / H, 1, 1 - y0 / H ] }
    a = np.asarray( alpha, np.float32 ) / 255.0
    save_png( out_dir / "walltext_trans.png", a, "L" )
    save_png( out_dir / "walltext_color.png", np.ones( ( H, W, 3 ), np.float32 ) * srgb( ( 58, 58, 60 ) ) )
    write_text( out_dir / "cb_walltext.vmat", vmat_text( {
        "TextureColor": f"{RESOURCE}/walltext_color.png", "TextureTranslucency": f"{RESOURCE}/walltext_trans.png",
        "TextureNormal": "materials/default/default_normal.tga", "TextureRoughness": "[0.550000 0.550000 0.550000 0.000000]",
        "TextureAmbientOcclusion": "materials/default/default_ao.tga" },
        extra={ "F_ALPHA_TEST": "1", "g_flAlphaTestReference": "0.5", "g_flAntiAliasedEdgeStrength": "1" } ) )
    return layout


def arrow( d, glyph, box, colour ):
    """ A wayfinding arrow (or the information 'i') drawn in box. """
    x0, y0, x1, y1 = box
    cx, cy, s = ( x0 + x1 ) / 2, ( y0 + y1 ) / 2, ( y1 - y0 ) * 0.36
    if glyph == "i":
        d.ellipse( ( cx - s, cy - s, cx + s, cy + s ), outline=colour, width=int( s * 0.16 ) )
        d.text( ( cx, cy + s * 0.05 ), "i", font=font( "Dinish-Bold.ttf", int( s * 1.4 ) ), fill=colour, anchor="mm" )
        return
    turn = { "→": 0.0, "↓": 90.0, "←": 180.0, "↑": 270.0 }[glyph]
    pts = [ ( -1.0, -0.22 ), ( 0.25, -0.22 ), ( 0.25, -0.62 ), ( 1.0, 0.0 ), ( 0.25, 0.62 ), ( 0.25, 0.22 ), ( -1.0, 0.22 ) ]
    c, s_ = math.cos( math.radians( turn ) ), math.sin( math.radians( turn ) )
    d.polygon( [ ( cx + s * ( x * c - y * s_ ), cy + s * ( x * s_ + y * c ) ) for x, y in pts ], fill=colour )


def running_figure( d, cx, cy, s, colour ):
    """ The exit signs' running figure, in thick strokes, and the door it runs to. """
    w = max( 2, int( s * 0.16 ) )
    head = ( cx + s * 0.18, cy - s * 0.72 )
    d.ellipse( ( head[0] - s * 0.13, head[1] - s * 0.13, head[0] + s * 0.13, head[1] + s * 0.13 ), fill=colour )
    hip = ( cx - s * 0.05, cy + s * 0.12 )
    neck = ( cx + s * 0.1, cy - s * 0.48 )
    for a, b in ( ( neck, hip ), ( neck, ( cx + s * 0.42, cy - s * 0.2 ) ), ( ( cx + s * 0.42, cy - s * 0.2 ), ( cx + s * 0.58, cy - s * 0.42 ) ),
                  ( neck, ( cx - s * 0.25, cy - s * 0.25 ) ), ( ( cx - s * 0.25, cy - s * 0.25 ), ( cx - s * 0.45, cy - s * 0.05 ) ),
                  ( hip, ( cx + s * 0.3, cy + s * 0.42 ) ), ( ( cx + s * 0.3, cy + s * 0.42 ), ( cx + s * 0.25, cy + s * 0.82 ) ),
                  ( hip, ( cx - s * 0.32, cy + s * 0.45 ) ), ( ( cx - s * 0.32, cy + s * 0.45 ), ( cx - s * 0.62, cy + s * 0.55 ) ) ):
        d.line( ( a, b ), fill=colour, width=w, joint="curve" )


def build_signs( out_dir, art_layout ):
    W = H = 2048
    image = Image.new( "RGB", ( W, H ), ( 52, 54, 56 ) )
    d = ImageDraw.Draw( image )
    layout = {}

    def box( key, x0, y0, x1, y1 ):
        layout[key] = [ ( x0 + 1 ) / W, 1 - ( y1 - 1 ) / H, ( x1 - 1 ) / W, 1 - ( y0 + 1 ) / H ]

    white, charcoal = ( 240, 238, 232 ), ( 52, 54, 56 )
    # Wayfinding panels: 1024 x 192, two a row, white on charcoal with an orange rule.
    for k, ( key, glyph, line1, line2 ) in enumerate( WAYFINDING ):
        x0, y0 = ( k % 2 ) * 1024, ( k // 2 ) * 192
        d.rectangle( ( x0, y0, x0 + 1023, y0 + 191 ), fill=charcoal )
        d.rectangle( ( x0 + 24, y0 + 22, x0 + 30, y0 + 170 ), fill=( 214, 112, 46 ) )
        arrow( d, glyph, ( x0 + 870, y0 + 16, x0 + 1010, y0 + 176 ), white )
        d.text( ( x0 + 58, y0 + 62 ), line1, font=font( "Dinish-Bold.ttf", 76 ), fill=white, anchor="lm" )
        d.text( ( x0 + 60, y0 + 140 ), line2, font=font( "Dinish-Regular.ttf", 44 ), fill=( 196, 196, 192 ), anchor="lm" )
        box( key, x0, y0, x0 + 1024, y0 + 192 )
    # Room plates: 512 x 128, four a row: charcoal letters on a pale plate.
    for k, text in enumerate( ROOMS ):
        x0, y0 = ( k % 4 ) * 512, 768 + ( k // 4 ) * 128
        d.rectangle( ( x0, y0, x0 + 511, y0 + 127 ), fill=( 226, 224, 218 ) )
        d.rectangle( ( x0 + 4, y0 + 4, x0 + 507, y0 + 123 ), outline=( 200, 198, 192 ), width=2 )
        d.text( ( x0 + 256, y0 + 66 ), text, font=font( "Dinish-Bold.ttf", 68 ), fill=charcoal, anchor="mm" )
        box( "room_" + text.lower().replace( " ", "_" ).replace( "í", "i" ), x0, y0, x0 + 512, y0 + 128 )
    # The works' labels: 320 x 224 white cards, six a row.
    names = sorted( art_layout, key=lambda k: art_layout[k]["label"] )
    for k, key in enumerate( names ):
        work = art_layout[key]
        x0, y0 = ( k % 6 ) * 340 + 8, 1152 + ( k // 6 ) * 232
        d.rectangle( ( x0, y0, x0 + 319, y0 + 223 ), fill=( 246, 245, 241 ) )
        ink = ( 30, 30, 32 )
        d.text( ( x0 + 18, y0 + 30 ), work["artist"], font=font( "Dinish-Bold.ttf", 25 ), fill=ink, anchor="lm" )
        d.text( ( x0 + 18, y0 + 60 ), f"({work['life'].replace( ' – ', '–' )})", font=font( "Dinish-Regular.ttf", 21 ), fill=ink, anchor="lm" )
        title_face = font( "Dinish-Italic.ttf", 24 )
        for j, line in enumerate( wrap( work["title"], title_face, 284 )[:2] ):
            d.text( ( x0 + 18, y0 + 100 + j * 28 ), line, font=title_face, fill=ink, anchor="lm" )
        d.text( ( x0 + 18, y0 + 162 ), f"{work['year']}  ·  {work['technique']}", font=font( "Dinish-Regular.ttf", 19 ), fill=ink, anchor="lm" )
        d.text( ( x0 + 18, y0 + 192 ), "Colección del museo", font=font( "Dinish-Regular.ttf", 18 ), fill=( 90, 90, 92 ), anchor="lm" )
        box( f"label_{key}", x0, y0, x0 + 320, y0 + 224 )
    # The cafe's menu board: chalk on black, in the labels' two empty places.
    x0, y0, x1, y1 = 1368, 1616, 2040, 1816
    d.rectangle( ( x0, y0, x1, y1 ), fill=( 26, 28, 28 ) )
    d.rectangle( ( x0 + 6, y0 + 6, x1 - 6, y1 - 6 ), outline=( 120, 92, 60 ), width=5 )
    chalk = ( 232, 230, 220 )
    for column, ( head, items ) in enumerate( MENU ):
        cx = x0 + 26 + column * 326
        d.text( ( cx, y0 + 34 ), head, font=font( "Mina-Bold.ttf", 34 ), fill=chalk, anchor="lm" )
        for j, ( item, price ) in enumerate( items ):
            yy = y0 + 76 + j * 28
            d.text( ( cx, yy ), item, font=font( "Dinish-Regular.ttf", 23 ), fill=chalk, anchor="lm" )
            d.text( ( cx + 282, yy ), price, font=font( "Dinish-Regular.ttf", 23 ), fill=chalk, anchor="rm" )
    box( "menu", x0, y0, x1, y1 )
    # Plates: 512 x 224: the hours, the rules, the museum's name, staff only.
    for k, ( key, line1, line2 ) in enumerate( PLATES ):
        x0, y0 = k * 512, 1824
        d.rectangle( ( x0, y0, x0 + 511, y0 + 223 ), fill=charcoal )
        size = 50
        while font( "Dinish-Bold.ttf", size ).getlength( line1 ) > 470:
            size -= 2
        d.text( ( x0 + 256, y0 + 80 ), line1, font=font( "Dinish-Bold.ttf", size ), fill=white, anchor="mm" )
        small = 28
        while font( "Dinish-Regular.ttf", small ).getlength( line2 ) > 470:
            small -= 1
        d.text( ( x0 + 256, y0 + 150 ), line2, font=font( "Dinish-Regular.ttf", small ), fill=( 200, 200, 196 ), anchor="mm" )
        box( f"plate_{key}", x0, y0, x0 + 512, y0 + 224 )
    save_png( out_dir / "signs_color.png", np.asarray( image, np.float32 ) / 255.0 )
    write_text( out_dir / "cb_signs.vmat", vmat_text( {
        "TextureColor": f"{RESOURCE}/signs_color.png", "TextureNormal": "materials/default/default_normal.tga",
        "TextureRoughness": "[0.420000 0.420000 0.420000 0.000000]", "TextureAmbientOcclusion": "materials/default/default_ao.tga" } ) )
    # The exit sign: white SALIDA and the running figure on green, 512 x 256, self-lit (a lamp behind its face).
    exit_image = Image.new( "RGB", ( 512, 256 ), ( 0, 132, 72 ) )
    e = ImageDraw.Draw( exit_image )
    running_figure( e, 120, 128, 84, ( 250, 252, 248 ) )
    e.rectangle( ( 196, 44, 204, 212 ), fill=( 250, 252, 248 ) )
    e.text( ( 352, 128 ), "SALIDA", font=font( "Dinish-Bold.ttf", 76 ), fill=( 250, 252, 248 ), anchor="mm" )
    save_png( out_dir / "exit_color.png", np.asarray( exit_image, np.float32 ) / 255.0 )
    write_text( out_dir / "cb_exit.vmat", vmat_text( {
        "TextureColor": f"{RESOURCE}/exit_color.png", "TextureNormal": "materials/default/default_normal.tga",
        "TextureRoughness": "[0.300000 0.300000 0.300000 0.000000]", "TextureAmbientOcclusion": "materials/default/default_ao.tga",
        "TextureSelfIllumMask": "[1.000000 1.000000 1.000000 0.000000]" },
        extra={ "F_SELF_ILLUM": "1", "g_flSelfIllumBrightness": "2.2", "g_flSelfIllumAlbedoFactor": "1.0",
                "g_vSelfIllumTint": "[1.000000 1.000000 1.000000 0.000000]" } ) )
    return layout


FACADE = [ ( "oeste", "galería oeste" ), ( "norte", "galería norte" ), ( "este", "sala este" ), ( "cafe", "cafetería" ) ]


def build_letters( out_dir ):
    """ The galleries' names in the same grey letters as the South Gallery's (cerroblanco_materials.labels), four
    lines of 2048 x 256 (8:1), alpha tested. """
    W, H = 2048, 1024
    alpha = Image.new( "L", ( W, H ), 0 )
    d = ImageDraw.Draw( alpha )
    layout = {}
    for k, ( key, text ) in enumerate( FACADE ):
        y0 = k * 256
        d.text( ( W / 2, y0 + 128 ), text, font=font( "Dinish-Regular.ttf", 170 ), fill=255, anchor="mm" )
        layout[key] = [ 0.0, 1 - ( y0 + 256 ) / H, 1.0, 1 - y0 / H ]
    save_png( out_dir / "letters_trans.png", np.asarray( alpha, np.float32 ) / 255.0, "L" )
    save_png( out_dir / "letters_color.png", np.ones( ( H // 4, W // 4, 3 ), np.float32 ) * srgb( ( 92, 92, 92 ) ) )
    write_text( out_dir / "cb_letters.vmat", vmat_text( {
        "TextureColor": f"{RESOURCE}/letters_color.png", "TextureTranslucency": f"{RESOURCE}/letters_trans.png",
        "TextureNormal": "materials/default/default_normal.tga", "TextureRoughness": "[0.600000 0.600000 0.600000 0.000000]",
        "TextureAmbientOcclusion": "materials/default/default_ao.tga" },
        extra={ "F_ALPHA_TEST": "1", "g_flAlphaTestReference": "0.5", "g_flAntiAliasedEdgeStrength": "1" }, metal=0.6 ) )
    return layout


def main( argv=None ):
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--out", type=Path, default=ROOT / "Assets", help="the Assets folder to write into (or a staging copy)" )
    parser.add_argument( "--only", nargs="*", choices=( "art", "text", "signs", "letters" ) )
    parser.add_argument( "--sheet", type=Path, help="also write a small picture of the art sheet" )
    args = parser.parse_args( argv )
    out_dir = args.out / RESOURCE
    out_dir.mkdir( parents=True, exist_ok=True )
    layout_path = out_dir / "layout.json"
    layout = json.loads( layout_path.read_text( encoding="utf-8" ) ) if layout_path.exists() else {}
    only = set( args.only or ( "art", "text", "signs", "letters" ) )
    if "art" in only or "art" not in layout:
        print( "art:" )
        layout["art"] = build_art( out_dir )
    if "text" in only:
        layout["walltext"] = build_walltext( out_dir )
    if "signs" in only:
        layout["signs"] = build_signs( out_dir, layout["art"] )
    if "letters" in only:
        layout["letters"] = build_letters( out_dir )
    write_text( layout_path, json.dumps( layout, indent=1, ensure_ascii=False ) + "\n" )
    if args.sheet:
        with Image.open( out_dir / "art_color.png" ) as im:
            im.resize( ( 1024, 1024 ), Image.LANCZOS ).save( args.sheet )
    print( f"wrote {out_dir}" )


if __name__ == "__main__":
    main()
