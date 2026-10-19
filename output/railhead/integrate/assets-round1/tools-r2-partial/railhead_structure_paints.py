"""
The structure area's own paints for Railhead (round 2): textures derived from the project's existing ones, so the
station's precast parapets, the shed's roof sarking, the footbridge's side panels and the goods shed's doors get the
colours real ones have without changing any other area's material.

    python Tools/railhead_structure_paints.py <root>        # writes <root>/materials/railhead/structure/*

<root> is a folder laid out as Assets (a stage, or Assets itself). Every paint is named rhs_*: railhead_map gives
rw_* paints railhead_materials' vmats, so these carry their own material_overrides (apply()).
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path( __file__ ).resolve().parents[1]
ASSETS = ROOT / "Assets"
FOLDER = "materials/railhead/structure"

# name: ( base vmat, how its colour map is remade, tile units, roughness scale )
#   ( "grade", target sRGB mean, saturation kept, blur radius in px, contrast kept )
PAINTS = {
    # 1970s precast parapets: mid-grey (RAL 7032-ish under a station's grime), smooth with fine pores, not the
    # blotchy cast-in-situ concrete the base texture is.
    "rhs_precast": ( "materials/railhead/rw_concrete.vmat", ( 132.0, 131.0, 125.0 ), 0.35, 3, 0.45, 256.0, 1.05 ),
    # The dark wash under brackets and drips on concrete: rust-brown grey.
    "rhs_grime": ( "materials/railhead/rw_concrete_dark.vmat", ( 70.0, 63.0, 55.0 ), 0.5, 2, 0.6, 256.0, 1.0 ),
    # Timber sarking under the shed's slate: weathered grey-brown, low chroma (planks_dark read as red-brown boards).
    "rhs_sarking": ( "materials/buildings/planks_dark.vmat", ( 104.0, 95.0, 84.0 ), 0.3, 0, 0.9, 96.0, 1.0 ),
    # The same boarding by the smoke lantern and the valley, blackened by a century of locomotive smoke.
    "rhs_sarking_soot": ( "materials/buildings/planks_dark.vmat", ( 58.0, 55.0, 51.0 ), 0.2, 0, 0.7, 96.0, 1.0 ),
    # The footbridge's side panels: DB blue-grey (RAL 7031-ish), lighter than the anthracite girders under them.
    "rhs_bridge_panel": ( "materials/railhead/rw_steel_dark.vmat", ( 110.0, 120.0, 126.0 ), 1.0, 0, 1.0, 128.0, 1.0 ),
    # Goods shed doors: boards painted fir green (RAL 6009), worn to the grain at the edges.
    "rhs_door_green": ( "materials/buildings/planks.vmat", ( 50.0, 66.0, 54.0 ), 0.25, 0, 0.8, 96.0, 1.0 ),
}


def _keys( text ):
    out = {}
    for line in text.splitlines():
        parts = line.strip().split( None, 1 )
        if len( parts ) == 2 and parts[1].startswith( '"' ):
            out[parts[0]] = parts[1].strip().strip( '"' )
    return out


def _blur( a, r ):
    if r <= 0:
        return a
    # A separable box blur, three passes (close to a Gaussian), wrapping so the map still tiles.
    for _ in range( 3 ):
        for axis in ( 0, 1 ):
            acc = np.zeros_like( a )
            for d in range( -r, r + 1 ):
                acc += np.roll( a, d, axis=axis )
            a = acc / ( 2 * r + 1 )
    return a


def colour_map( name, src ):
    """ The paint's colour map (uint8 RGB) remade from the base's. """
    from PIL import Image
    _, target, sat, blur, contrast, _, _ = PAINTS[name]
    img = Image.open( src ).convert( "RGB" )
    if max( img.size ) > 1024:
        img = img.resize( ( 1024, 1024 ), Image.LANCZOS )
    a = np.asarray( img, float ) / 255.0
    lin = np.where( a <= 0.04045, a / 12.92, ( ( a + 0.055 ) / 1.055 ) ** 2.4 )
    lum = lin @ np.array( ( 0.2126, 0.7152, 0.0722 ) )
    lin = lum[..., None] + ( lin - lum[..., None] ) * sat
    if blur:
        lin = 0.5 * lin + 0.5 * _blur( lin, blur )
    mean = lin.reshape( -1, 3 ).mean( 0 )
    lin = mean + ( lin - mean ) * contrast
    t = np.asarray( target, float ) / 255.0
    t_lin = np.where( t <= 0.04045, t / 12.92, ( ( t + 0.055 ) / 1.055 ) ** 2.4 )
    lin = lin * ( t_lin / np.maximum( lin.reshape( -1, 3 ).mean( 0 ), 1e-4 ) )
    lin = np.clip( lin, 0.0, 1.0 )
    s = np.where( lin <= 0.0031308, lin * 12.92, 1.055 * lin ** ( 1 / 2.4 ) - 0.055 )
    return ( np.clip( s, 0, 1 ) * 255 + 0.5 ).astype( np.uint8 )


def write( root ):
    """ Writes every paint's colour map and vmat under root (laid out as Assets). """
    from PIL import Image
    root = Path( root )
    folder = root / FOLDER
    folder.mkdir( parents=True, exist_ok=True )
    for name, ( base, *_ , rough ) in PAINTS.items():
        keys = _keys( ( ASSETS / base ).read_text() )
        rgb = colour_map( name, ASSETS / keys["TextureColor"] )
        Image.fromarray( rgb ).save( folder / f"{name}_color.png" )
        vmat = "\n".join( [
            "// Tools/railhead_structure_paints.py",
            '"Layer0"',
            "{",
            '    shader "shaders/complex.shader"',
            '    F_SPECULAR "1"',
            f'    g_flRoughnessScaleFactor "{rough}"',
            '    g_flMetalness "0.00"',
            f'    TextureColor "{FOLDER}/{name}_color.png"',
            f'    TextureNormal "{keys["TextureNormal"]}"',
            f'    TextureRoughness "{keys["TextureRoughness"]}"',
            '    TextureAmbientOcclusion "materials/default/default_ao.tga"',
            '    g_vColorTint "[1.0 1.0 1.0 1.0]"',
            '    g_flModelTintAmount "1.0"',
            "}", "" ] )
        ( folder / f"{name}.vmat" ).write_text( vmat )
        print( f"wrote {FOLDER}/{name}.vmat" )


def apply( models ):
    """ Points every model's rhs_* paints at their vmats and tile sizes. """
    for model in models.values():
        for paint in model.polygons:
            if paint in PAINTS:
                model.material_overrides[paint] = f"{FOLDER}/{paint}.vmat"
                model.tile_overrides[paint] = PAINTS[paint][5]


if __name__ == "__main__":
    if len( sys.argv ) != 2:
        sys.exit( __doc__ )
    write( sys.argv[1] )
