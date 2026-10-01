"""
The Oceanarium map's materials: the aquarium's own from my_project (its materials, their textures and its five
shaders), copied into hc1 at the same paths, and a material for every aquarium part my_project tints at runtime.

    python Tools/oceanarium_assets.py [--check]

my_project draws each part of the aquarium with its own ModelRenderer, tinted (ModelRenderer.Tint). hc1 draws the
aquarium as a few models, so a tinted part gets a material of its own: a copy of its material with the tint multiplied
into g_vColorTint, in materials/oceanarium/. The aquarium's own shaders take no g_vColorTint, so a part drawn in one of
those (the touch pool's mossy stones) gets a tinted copy of its colour map instead. Parts my_project draws in the
engine's materials/default/white.vmat get a plain material on a white texture, tinted the same way.

- Paints: the map's models paint the aquarium's parts "core_<part key>" (core_rock_sea, core_limestone, ...), so they
  can't clash with building_textures' paints. core_paints() gives each one's material and texture repeat, which
  Tools/oceanarium_map.py also uses for its own walls.
- The copies keep my_project's .meta files (only a guid each), and the .shader sources: the editor compiles them.
- --check lists what it would copy or write, without writing.
"""
import argparse
import re
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

import aquarium_core as A

ROOT = Path( __file__ ).resolve().parent.parent
ASSETS = ROOT / "Assets"
SOURCE = A.MY_PROJECT / "Assets"
OWN = "materials/oceanarium"
WHITE_TEXTURE = "textures/oceanarium/white_color.png"
FLAT_ROUGH = "textures/oceanarium/satin_rough.png"
SHADERS = ( "aquarium_current", "aquarium_pool_floor", "aquarium_pool_plant", "aquarium_pool_water", "aquarium_reef" )
WHITE = "materials/default/white.vmat"

# How many units one repeat of each tiling aquarium texture covers: the median, by area, of world size over UV size
# across each part's polygons in aquarium.txt (measured 2026-10-01). The map's own walls in these materials use it.
# The rest are painted once over a whole piece (the rotunda's floor, the backdrops, signs), so the map doesn't reuse
# them on new surfaces, and they get 128.
TILES = {
    "limestone": 128.0, "navy": 96.0, "stone_dark": 64.0, "ceiling": 160.0, "plaster": 128.0, "gallery_plaster": 128.0,
    "concrete": 48.0, "metal": 48.0, "steel": 32.0, "wood": 48.0, "paving": 96.0, "floor_gang": 240.0,
    "floor_tunnel": 96.0, "rock": 96.0, "rock_sea": 96.0, "rock_sea_far": 96.0, "sand": 160.0, "tunnel_glass": 256.0,
    "glass": 138.0, "fabric": 48.0, "fabric_light": 32.0, "black": 32.0, "cream": 32.0, "soil": 32.0,
    "gallery_rail": 64.0, "led": 64.0,
}


def paint( key ):
    return f"core_{key}"


def tinted( part ):
    return part.material == WHITE or any( abs( c - 1.0 ) > 1e-6 for c in part.tint )


def material_of( part ):
    """ The material hc1 draws this part with. """
    return f"{OWN}/{part.key}.vmat" if tinted( part ) else part.material


def core_paints( parts ):
    """ { paint: ( material, tile units ) } for every aquarium part. """
    return { paint( k ): ( material_of( p ), TILES.get( k, 128.0 ) ) for k, p in parts.items() }


def textures_of( vmat_text ):
    return re.findall( r'^\s*Texture\w*\s+"([^"]+)"', vmat_text, re.M )


def tint_text( text, tint ):
    """ The vmat with tint multiplied into g_vColorTint. """
    def scale( m ):
        values = [ float( v ) for v in m.group( 1 ).split() ]
        values[:3] = [ v * t for v, t in zip( values[:3], tint ) ]
        return 'g_vColorTint "[' + " ".join( f"{v:.6f}" for v in values ) + ']"'
    out, count = re.subn( r'g_vColorTint "\[([^\]]+)\]"', scale, text )
    if count == 0:
        out = text.replace( 'shader "', 'g_vColorTint "[{:.6f} {:.6f} {:.6f} 1.000000]"\n\tshader "'.format( *tint ), 1 )
    return out


def tint_texture( text, part, dry, changed ):
    """ For the aquarium's own shaders, which take no g_vColorTint: the vmat on a tinted copy of its colour map. """
    m = re.search( r'TextureColor "([^"]+)"', text )
    source = SOURCE / m.group( 1 )
    rel = f"textures/oceanarium/{part.key}_color.png"
    from io import BytesIO
    image = Image.open( source ).convert( "RGBA" )
    a = np.asarray( image ).astype( np.float32 )
    a[..., :3] *= np.array( part.tint, np.float32 )
    buf = BytesIO()
    Image.fromarray( np.clip( a + 0.5, 0, 255 ).astype( np.uint8 ), "RGBA" ).save( buf, format="PNG", optimize=True )
    if write_if_changed( rel, buf.getvalue(), dry ):
        changed.append( rel )
    return text.replace( m.group( 0 ), f'TextureColor "{rel}"' )


def plain_vmat( part ):
    r, g, b = part.tint
    return ( f"// {part.name}: plain paint (Tools/oceanarium_assets.py), as my_project draws it in white.vmat tinted\n"
             "Layer0\n{\n"
             '\tshader "shaders/complex.shader"\n'
             '\tg_flModelTintAmount "1.000"\n'
             f'\tg_vColorTint "[{r:.6f} {g:.6f} {b:.6f} 1.000000]"\n'
             f'\tTextureColor "{WHITE_TEXTURE}"\n'
             '\tTextureNormal "materials/default/default_normal.tga"\n'
             f'\tTextureRoughness "{FLAT_ROUGH}"\n'
             '\tg_flRoughnessScaleFactor "1.000"\n'
             '\tg_bFogEnabled "1"\n'
             '\tg_flMetalness "0.000"\n'
             "}\n" )


def copy_file( rel, dry ):
    """ my_project's file (and its .meta) to the same path in hc1, if it differs. Returns whether it would change. """
    src, dst = SOURCE / rel, ASSETS / rel
    if not src.exists():
        raise FileNotFoundError( src )
    changed = False
    for s, d in ( ( src, dst ), ( src.with_name( src.name + ".meta" ), dst.with_name( dst.name + ".meta" ) ) ):
        if not s.exists():
            continue
        if d.exists() and d.read_bytes() == s.read_bytes():
            continue
        changed = True
        if not dry:
            d.parent.mkdir( parents=True, exist_ok=True )
            shutil.copyfile( s, d )
    return changed


def write_if_changed( rel, data, dry ):
    dst = ASSETS / rel
    if isinstance( data, str ):
        data = data.encode( "utf-8" )
    if dst.exists() and dst.read_bytes() == data:
        return False
    if not dry:
        dst.parent.mkdir( parents=True, exist_ok=True )
        dst.write_bytes( data )
    return True


def flat_png( value, rgb=True ):
    from io import BytesIO
    a = np.full( ( 4, 4, 3 ) if rgb else ( 4, 4 ), value, np.uint8 )
    buf = BytesIO()
    Image.fromarray( a, "RGB" if rgb else "L" ).save( buf, format="PNG" )
    return buf.getvalue()


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--check", action="store_true", help="list what would change, without writing" )
    args = parser.parse_args()
    dry = args.check
    parts = A.read( parts_only=True ).parts
    changed = []

    # The materials the parts use. my_project's fish, jellies and end-wall pictures (AquariumLife) aren't ported.
    vmats = { p.material for p in parts.values() if p.material != WHITE }
    textures = set()
    for rel in sorted( vmats ):
        if copy_file( rel, dry ):
            changed.append( rel )
        textures |= set( textures_of( ( SOURCE / rel ).read_text( encoding="utf-8" ) ) )
    for rel in sorted( textures ):
        if rel.startswith( "materials/default/" ):
            continue    # the engine's
        if copy_file( rel, dry ):
            changed.append( rel )
    for name in SHADERS:
        if copy_file( f"shaders/{name}.shader", dry ):
            changed.append( f"shaders/{name}.shader" )

    if write_if_changed( WHITE_TEXTURE, flat_png( 255 ), dry ):
        changed.append( WHITE_TEXTURE )
    if write_if_changed( FLAT_ROUGH, flat_png( 150, rgb=False ), dry ):
        changed.append( FLAT_ROUGH )
    for key, part in sorted( parts.items() ):
        if not tinted( part ):
            continue
        if part.material == WHITE:
            text = plain_vmat( part )
        else:
            source = ( SOURCE / part.material ).read_text( encoding="utf-8" )
            if 'shader "shaders/complex.shader"' in source:
                source = tint_text( source, part.tint )
            else:
                source = tint_texture( source, part, dry, changed )
            text = f"// {part.name}: {part.material} tinted as my_project tints it (Tools/oceanarium_assets.py)\n" + source
        if write_if_changed( material_of( part ), text, dry ):
            changed.append( material_of( part ) )

    verb = "would change" if dry else "changed"
    print( f"{len( changed )} file(s) {verb}" + ( ":" if changed and dry else "" ) )
    if dry:
        for rel in changed:
            print( f"  {rel}" )


if __name__ == "__main__":
    main()
