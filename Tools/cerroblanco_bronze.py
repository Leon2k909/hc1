"""
Cerro Blanco's cast bronze (cb_bronze): the garden circle's sphere, the gallery's smaller one and the busts on the
gallery plinths.

cb_bronze was a flat paint, metalness 0.9 tinted (92, 66, 40): as a metal its colour is its reflectance, about a tenth
in linear light, so the sphere mirrored the garden at a tenth of its brightness and stayed near black in full sun, with
no lit side (2026-10-24, the user: "this looks bad"). An outdoor bronze is cast metal under a waxed chemical patina, and
the patina is what you see: brown, satin, lit by the sun like a dielectric, with soft highlights from the metal under
it, and the metal itself only where hands and weather wear it through. So it's a textured material:

- colour: the patina's browns (umber to tobacco) in broad blotches, faint grey-green run-off streaks down the surface,
  and a few small worn spots of bright bronze;
- metalness 0.55 in the patina (the metal shining through the wax and oxide), 0.92 where it's worn;
- roughness 0.44 in the patina, rougher in the streaks, 0.26 on the worn spots;
- a faint cast surface in the normal map.

Everything tiles both ways, 2048 x 1024: a sphere's UVs (sphere()) go once round its circumference and once pole to
pole, which is 2:1, so the texels are square; the busts' world-projected UVs (64 a tile) take the same pictures.

sphere() draws a sphere smooth enough that its outline doesn't show facets (64 x 32; the old one was 24 x 12), its
normals per vertex and its UVs as above. Drawn only: its collision is bronze_sphere's hull.

    python Tools/cerroblanco_bronze.py [--out <materials dir>]    writes the textures and cb_bronze.vmat
"""
import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image

import map_kit as K

PAINT = "cb_bronze"
RESOURCE = "materials/cerroblanco"
SIZE = ( 1024, 2048 )            # rows (v, pole to pole), columns (u, round the sphere)
SIDES, RINGS = 64, 32

UMBER, BROWN, TOBACCO = ( 84, 62, 42 ), ( 112, 82, 56 ), ( 140, 102, 66 )
VERDIGRIS = ( 98, 102, 82 )      # the run-off's grey-green
WORN = ( 182, 138, 88 )          # bright bronze where the patina's worn through


def linear( srgb ):
    c = np.asarray( srgb, float ) / 255.0
    return np.where( c <= 0.04045, c / 12.92, ( ( c + 0.055 ) / 1.055 ) ** 2.4 )


def to_srgb( lin ):
    c = np.clip( lin, 0.0, 1.0 )
    return np.where( c <= 0.0031308, c * 12.92, 1.055 * c ** ( 1 / 2.4 ) - 0.055 ) * 255.0


def noise( rng, sigma_v, sigma_u=None ):
    """ Gaussian-filtered white noise that tiles both ways (filtered in the frequency domain), mean 0 and spread 1.
    sigma in pixels, down v and across u. """
    sigma_u = sigma_v if sigma_u is None else sigma_u
    f = np.fft.fft2( rng.standard_normal( SIZE ) )
    kv, ku = np.fft.fftfreq( SIZE[0] )[:, None], np.fft.fftfreq( SIZE[1] )[None, :]
    out = np.real( np.fft.ifft2( f * np.exp( -2 * math.pi ** 2 * ( ( sigma_v * kv ) ** 2 + ( sigma_u * ku ) ** 2 ) ) ) )
    return ( out - out.mean() ) / out.std()


def pictures( seed=241024 ):
    rng = np.random.default_rng( seed )
    broad, mid, fine = noise( rng, 60 ), noise( rng, 14 ), noise( rng, 1.5 )
    # Run-off: thin lines down the surface, fading in and out along their length.
    streak = np.clip( ( noise( rng, 140, 6 ) - 1.3 ) * 0.9, 0, 1 ) * np.clip( 0.5 + 0.5 * noise( rng, 90 ), 0, 1 )
    # Wear: soft, rubbed patches that never quite reach bare metal.
    worn = 0.7 * np.clip( ( noise( rng, 50 ) - 1.4 ) * 0.45, 0, 1 ) ** 1.5
    t = np.clip( 0.5 + 0.2 * broad + 0.08 * mid, 0, 1 )[..., None]
    colour = np.where( t < 0.5, linear( UMBER ) + ( linear( BROWN ) - linear( UMBER ) ) * t * 2,
                       linear( BROWN ) + ( linear( TOBACCO ) - linear( BROWN ) ) * ( t - 0.5 ) * 2 )
    colour = colour + ( linear( VERDIGRIS ) - colour ) * ( 0.35 * streak )[..., None]
    colour = colour + ( linear( WORN ) - colour ) * worn[..., None]
    colour = colour * ( 1 + 0.04 * fine )[..., None]
    metal = np.clip( 0.55 + 0.37 * worn - 0.2 * streak, 0, 1 )
    rough = np.clip( 0.44 + 0.04 * mid + 0.08 * streak - 0.18 * worn + 0.02 * fine, 0.2, 0.7 )
    # The cast surface: a faint waviness and a few shallow pits, flattened where it's worn smooth.
    height = ( 0.6 * noise( rng, 25 ) - 0.5 * np.clip( noise( rng, 1.2 ) - 2.2, 0, None ) ) * ( 1 - 0.7 * worn )
    du = ( np.roll( height, -1, 1 ) - np.roll( height, 1, 1 ) ) / 2
    dv = ( np.roll( height, -1, 0 ) - np.roll( height, 1, 0 ) ) / 2
    n = np.stack( ( -du * 0.35, dv * 0.35, np.ones_like( height ) ), axis=-1 )
    n /= np.linalg.norm( n, axis=-1, keepdims=True )
    return { "color": to_srgb( colour ), "metal": metal * 255, "rough": rough * 255, "normal": 127.5 + 127.5 * n }


def write_materials( out=None ):
    """ The textures and cb_bronze.vmat, into out (the materials/cerroblanco folder; Assets' by default). """
    out = Path( out ) if out else K.ASSETS / RESOURCE
    out.mkdir( parents=True, exist_ok=True )
    for name, data in pictures().items():
        if data.ndim == 2:
            data = np.repeat( data[..., None], 3, axis=2 )
        temp = out / f"{PAINT}_{name}.writing.png"
        Image.fromarray( np.clip( np.rint( data ), 0, 255 ).astype( np.uint8 ) ).save( temp )
        temp.replace( out / f"{PAINT}_{name}.png" )
    text = ( '// Tools/cerroblanco_bronze.py\n"Layer0"\n{\n    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
             '    F_METALNESS_TEXTURE "1"\n    g_flMetalness "0"\n    g_flRoughnessScaleFactor "1"\n'
             '    g_vColorTint "[1 1 1 1]"\n    g_flModelTintAmount "1"\n'
             f'    TextureColor "{RESOURCE}/{PAINT}_color.png"\n'
             f'    TextureNormal "{RESOURCE}/{PAINT}_normal.png"\n'
             f'    TextureRoughness "{RESOURCE}/{PAINT}_rough.png"\n'
             f'    TextureMetalness "{RESOURCE}/{PAINT}_metal.png"\n'
             '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n}\n' )
    K.write_text( out / f"{PAINT}.vmat", text )


def sphere( m, centre, r, paint=PAINT ):
    """ A smooth sphere of radius r round centre (plan e, n, z), its UVs once round and once pole to pole. """
    c = np.asarray( centre, float )

    def at( i, k ):
        t, p = math.pi * i / RINGS, 2 * math.pi * k / SIDES
        return np.array( ( math.sin( t ) * math.cos( p ), math.sin( t ) * math.sin( p ), math.cos( t ) ) )

    for i in range( RINGS ):
        for k in range( SIDES ):
            corners = [ ( i, k ), ( i, k + 1 ), ( i + 1, k + 1 ), ( i + 1, k ) ]
            if i == 0:
                corners = [ ( 0, k + 0.5 ), ( 1, k + 1 ), ( 1, k ) ]
            elif i == RINGS - 1:
                corners = [ ( i, k ), ( i, k + 1 ), ( RINGS, k + 0.5 ) ]
            d = [ at( a, b ) for a, b in corners ]
            pts = [ c + v * r for v in d ]
            uv = [ ( b / SIDES, a / RINGS ) for a, b in corners ]
            # Wound to face out, as cerroblanco_parts.card winds its faces.
            if np.dot( np.cross( pts[1] - pts[0], pts[2] - pts[0] ), sum( d ) ) < 0:
                pts, d, uv = pts[::-1], d[::-1], uv[::-1]
            m.polygon( paint, pts, normals=d, uv=uv )


if __name__ == "__main__":
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--out", help="where to write (laid out as materials/cerroblanco); Assets' by default" )
    write_materials( parser.parse_args().out )
