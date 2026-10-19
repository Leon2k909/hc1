"""
The reactor hall staged by stage_hall.py, rendered offline in Cycles through Tools/railhead_render.py (after the facades
 area's render wrapper).

    set RIVERDALE_STAGE=<dir laid out as Assets>   (default: this area's stage)
    set RIVERDALE_SCENE=riverdale_nohaze.scene     (stage_hall.py's scene without the volumetric haze, for clean renders)
    blender -b --factory-startup --python output/riverdale/aaa/hall/tools/render.py -- --views "" \
        --view name,e,n,z,te,tn,tz,fov ... [--size 1280x720] [--samples 48] [--out <dir>] [--exposure 1.6]

The scene, models and any material are read from the stage first, then from Assets. Belltower's window shader (the
rooms behind riverdale_materials' windows) is drawn as dark glossy glass with the room's picture glowing through it.
"""
import os
import re
import sys
from pathlib import Path

HERE = Path( __file__ ).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert( 0, str( ROOT / "Tools" ) )

import bpy  # noqa: E402
import railhead_render as RR  # noqa: E402

STAGE = Path( os.environ.get( "RIVERDALE_STAGE", str( HERE.parent / "stage" ) ) ).resolve()
EXTRA = [ Path( p ) for p in os.environ.get( "RIVERDALE_MATERIALS", str( ROOT / "output/riverdale/aaa/stage" ) ).split( ";" ) if p ]
SEARCH = [ STAGE ] + EXTRA + [ RR.ASSETS ]
RR.SCENE = STAGE / "scenes/maps/Riverdale" / os.environ.get( "RIVERDALE_SCENE", "riverdale.scene" )


def resolve( rel ):
    for base in SEARCH:
        p = base / rel
        if p.is_file():
            return p
    return RR.ASSETS / rel


_image = RR.image


def image( path, data=False ):
    if not path or RR.is_vector( path ):
        return None
    p = Path( path )
    if not p.is_absolute():
        p = resolve( path )
    return _image( str( p ), data )


def parse_vmat( path ):
    text = resolve( path ).read_text( encoding="utf-8", errors="replace" )
    shader = re.search( r'shader\s+"([^"]+)"', text ).group( 1 )
    keys = dict( re.findall( r'^\s*(\w+)\s+"([^"]*)"', text, re.M ) )
    flags = { k: int( v ) for k, v in re.findall( r'^\s*(F_\w+)\s+(\d+)', text, re.M ) }
    keys.update( { k: str( v ) for k, v in flags.items() } )
    return shader, keys


def window_material( name, keys ):
    g = RR.Graph( name )
    p = g.node( "ShaderNodeBsdfPrincipled" )
    p.inputs["Base Color"].default_value = ( 0.003, 0.005, 0.006, 1.0 )
    p.inputs["Roughness"].default_value = 0.16
    back = image( keys.get( "TextureRoomBack", "" ) )
    if back is not None:
        tex = g.tex( back )
        g.link( tex.outputs["Color"], p.inputs["Emission Color"] )
        p.inputs["Emission Strength"].default_value = float( keys.get( "g_flInteriorBrightness", "0.13" ) ) * 1.6
    return g.finish( p.outputs[0] )


def material( path ):
    if path in RR.MATERIALS:
        return RR.MATERIALS[path]
    try:
        shader, keys = parse_vmat( path )
        if "belltower_window" in shader:
            mat = window_material( path, keys )
        elif "glass" in shader:
            mat = RR.glass_material( path, keys )
        else:
            mat = RR.standard_material( path, keys )
    except Exception as error:
        print( f"  {path}: {type( error ).__name__}: {error}" )
        g = RR.Graph( path )
        p = g.node( "ShaderNodeBsdfPrincipled" )
        p.inputs["Base Color"].default_value = ( 0.8, 0.0, 0.8, 1.0 )
        mat = g.finish( p.outputs[0] )
    RR.MATERIALS[path] = mat
    return mat


def map_model( path ):
    if os.environ.get( "RIVERDALE_SKIP" ) and any( s in path for s in os.environ["RIVERDALE_SKIP"].split( ";" ) ):
        return []
    text = resolve( path ).read_text( encoding="utf-8" )
    obj = resolve( re.search( r'filename = "([^"]+\.obj)"', text ).group( 1 ) )
    remaps = dict( re.findall( r'\{ from = "([^"]+)" to = "([^"]+)" \}', text ) )
    before = set( bpy.data.objects )
    bpy.ops.wm.obj_import( filepath=str( obj ), forward_axis="Y", up_axis="Z" )
    objects = [ o for o in bpy.data.objects if o not in before ]
    for o in objects:
        for slot in o.material_slots:
            if slot.material is None:
                continue
            mtl = re.sub( r"\.\d{3}$", "", slot.material.name )
            target = remaps.get( mtl + ".vmat" )
            if target:
                slot.material = material( target )
    return objects


RR.image = image
RR.parse_vmat = parse_vmat
RR.material = material
RR.map_model = map_model

if __name__ == "__main__":
    RR.main()
