"""
Railhead rendered offline in Cycles, to judge its shapes, materials and light against a reference without the editor.

    blender -b --factory-startup --python Tools/railhead_render.py -- [--views reference,concourse] [--size 1280x720]
        [--samples 64] [--out <dir>] [--cpu] [--threads N] [--no-trees] [--texture-limit 2048] [--exposure 2.0]
        [--haze 0.00004] [--bloom 0.6] [--view name,e,n,z,te,tn,tz,fov ...]

It reads Assets/scenes/maps/Railhead/railhead.scene as the game does:
- Every ModelRenderer. The map's own models come from their OBJs and their vmdls' remaps. The cloud oaks and beech
  bushes come from the local cloud cache (.sbox/cloud), exported once with Source2Viewer-CLI (VRF_CLI, or
  D:/tmp/hc1-mw22-tools/vrf) into the cache folder. Belltower's renderer exports the same three models, so its cache
  is used when it has them.
- The materials from their vmats:
  - complex.shader's colour, normal, roughness, AO, metalness, alpha test, translucency and self-illumination, with
    the backs of single-sided faces see-through, as the engine culls them;
  - glass.shader as the engine composites it: the view through tinted by the albedo, less a share by its roughness
    and AlbedoAbsorption that shows as a diffuse film, under a Fresnel reflection.
- The sun, the point lights and the sky panorama, turned as s&box wraps it round the world.
- VolumetricFogVolumes, as a homogeneous scattering medium in their bounds.
- The Look volume: s&box's ACES at railhead_map.SKY_EXPOSURE, the gradient fog, the colour temperature and the
  vignette, applied to the linear render. --bloom adds a soft glow round the brightest light, as a camera's Bloom
  would.

What it can't show as a match does:
- Cycles bounces light (--bounces), where the engine has the sky's ambient light, the envmap probes and SSAO, so
  shaded corners come out warmer and lighter than in a match.
- --haze fills the whole world with a thin scattering medium, for the sun's shafts through the roof. The engine only
  has that inside a VolumetricFogVolume.
- There are no particles, decal components, players or bots.

The views are railhead_preview.VIEWS plus REFERENCE_VIEWS: ( name, plan eye, plan target, horizontal fov ), with plan
( east, north, z ) at world ( north, -east, z ). --view adds one of your own. Each is written as <name>.png, with the
linear render as <name>.exr, to --out (default: the system temp folder's hc1_railhead_render/renders).
"""
import argparse
import ast
import json
import math
import os
import re
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path( __file__ ).resolve().parent.parent
ASSETS = ROOT / "Assets"
CLOUD = ROOT / ".sbox" / "cloud"
SCENE = ASSETS / "scenes/maps/Railhead/railhead.scene"
TEMP = Path( tempfile.gettempdir() ) / "hc1_railhead_render"
CACHE = TEMP / "cache"
# Belltower's renderer exports the same cloud trees; their glbs and textures are reused from there.
SHARED_CACHES = ( Path( tempfile.gettempdir() ) / "hc1_belltower_render" / "cache", )
VRF_CLI = Path( os.environ.get( "VRF_CLI", "D:/tmp/hc1-mw22-tools/vrf/Source2Viewer-CLI.exe" ) )

# OBJ ( a, b, c ) is model ( y, z, x ): ModelDoc reads an OBJ as Y-up (map_kit.obj_vector).
OBJ_TO_MODEL = Matrix( ( ( 0, 0, 1, 0 ), ( 1, 0, 0, 0 ), ( 0, 1, 0, 0 ), ( 0, 0, 0, 1 ) ) )
# glTF from Source2Viewer: metres, Y up.
GLTF_UNITS = 1.0 / 0.0254

# s&box's ACES (Hill's fit), as belltower_sky.py has it.
ACES_IN = np.array( ( ( 0.59719, 0.07600, 0.02840 ), ( 0.35458, 0.90834, 0.13383 ), ( 0.04823, 0.01566, 0.83777 ) ) )
ACES_OUT = np.array( ( ( 1.60475, -0.10208, -0.00327 ), ( -0.53108, 1.10813, -0.07276 ),
                       ( -0.07367, -0.00605, 1.07602 ) ) )

# Views to hold against the reference picture: a player on the concourse, between the head building's piers, looking
# down the shed to its south screen.
REFERENCE_VIEWS = [
    ( "reference", ( -40, 1230, 64 ), ( 60, -1300, 230 ), 85 ),
    ( "reference_wide", ( 0, 1280, 64 ), ( 0, -1300, 200 ), 95 ),
    ( "reference_high", ( 0, 1150, 300 ), ( 0, -1300, 380 ), 85 ),
]


def literal( path, name ):
    """ A module-level literal from a Tools script, read without importing it (they import numba, scipy and PIL). """
    tree = ast.parse( Path( path ).read_text( encoding="utf-8" ) )
    for node in tree.body:
        if isinstance( node, ast.Assign ):
            for target in node.targets:
                if isinstance( target, ast.Name ) and target.id == name:
                    return ast.literal_eval( node.value )
    raise KeyError( name )


def floats( text ):
    return [ float( v ) for v in str( text ).replace( "[", " " ).replace( "]", " " ).replace( ",", " " ).split() ]


def is_vector( text ):
    return str( text ).strip().startswith( "[" )


# ---------------------------------------------------------------------------------------------------------------------
# The scene file

def local_matrix( go ):
    p = floats( go.get( "Position", "0,0,0" ) )
    q = floats( go.get( "Rotation", "0,0,0,1" ) )
    s = floats( go.get( "Scale", "1,1,1" ) )
    rotation = Quaternion( ( q[3], q[0], q[1], q[2] ) ).to_matrix().to_4x4()
    return Matrix.Translation( p ) @ rotation @ Matrix.Diagonal( ( *s, 1.0 ) )


def read_scene():
    """ The enabled components that draw or light, each with its object's world matrix. """
    scene = json.loads( SCENE.read_text( encoding="utf-8" ) )
    found = { "models": [], "suns": [], "points": [], "sky": None, "fog": None, "look": {}, "volumes": [] }

    def walk( go, parent ):
        if go.get( "Enabled", True ) is False:
            return
        world = parent @ local_matrix( go )
        for c in go.get( "Components", [] ):
            if c.get( "__enabled", True ) is False:
                continue
            kind = c.get( "__type", "" )
            if kind == "Sandbox.ModelRenderer" and c.get( "Model" ):
                found["models"].append( ( c["Model"], world, floats( c.get( "Tint", "1,1,1,1" ) ) ) )
            elif kind == "Sandbox.DirectionalLight":
                found["suns"].append( ( world, floats( c["LightColor"] ) ) )
            elif kind == "Sandbox.PointLight":
                found["points"].append( ( world, floats( c["LightColor"] ), float( c.get( "Radius", 400 ) ) ) )
            elif kind == "Sandbox.SpotLight":
                found["points"].append( ( world, floats( c["LightColor"] ), float( c.get( "Radius", 400 ) ) ) )
            elif kind == "Sandbox.SkyBox2D":
                found["sky"] = ( c.get( "SkyMaterial" ), floats( c.get( "Tint", "1,1,1,1" ) ) )
            elif kind == "Sandbox.GradientFog":
                found["fog"] = c
            elif kind == "Sandbox.VolumetricFogVolume":
                found["volumes"].append( ( world, c ) )
            elif kind in ( "Sandbox.Tonemapping", "Sandbox.ColorGrading", "Sandbox.Vignette", "Sandbox.Bloom" ):
                found["look"][kind.split( "." )[1]] = c
        for child in go.get( "Children", [] ):
            walk( child, world )

    for go in scene["GameObjects"]:
        walk( go, Matrix.Identity( 4 ) )
    return found


# ---------------------------------------------------------------------------------------------------------------------
# Compiled cloud resources

def strip_guid( src, dst ):
    """ A copy of a compiled resource without its GUID block, which Source2Viewer-CLI can't read. """
    data = bytearray( Path( src ).read_bytes() )
    _, _, _, table_rel, count = struct.unpack_from( "<IHHII", data, 0 )
    table = 8 + table_rel
    entries = []
    for i in range( count ):
        at = table + i * 12
        rel, length = struct.unpack_from( "<II", data, at + 4 )
        entries.append( ( bytes( data[at:at + 4] ), at + 4 + rel, length ) )
    kept = [ e for e in entries if e[0] != b"GUID" ]
    for i, ( kind, absolute, length ) in enumerate( kept ):
        at = table + i * 12
        data[at:at + 4] = kind
        struct.pack_into( "<II", data, at + 4, absolute - ( at + 4 ), length )
    for i in range( len( kept ), count ):
        data[table + i * 12:table + i * 12 + 12] = b"\0" * 12
    struct.pack_into( "<I", data, 12, len( kept ) )
    Path( dst ).parent.mkdir( parents=True, exist_ok=True )
    Path( dst ).write_bytes( data )


def vrf( *args ):
    if not VRF_CLI.exists():
        raise RuntimeError( f"Source2Viewer-CLI not found at {VRF_CLI} (set VRF_CLI)" )
    return subprocess.run( [ str( VRF_CLI ), *map( str, args ) ], capture_output=True, text=True, timeout=600 ).stdout


def cached( relative ):
    """ A file in this renderer's cache, or in a shared one that already has it. """
    for root in SHARED_CACHES:
        p = root / relative
        if p.exists():
            return p
    return CACHE / relative


def cloud_file( resource ):
    """ A compiled cloud resource ( e.g. 'models/x.vmdl' ), GUID stripped, in the cache. """
    dst = cached( Path( "cloud" ) / ( resource + "_c" ) )
    if not dst.exists():
        src = CLOUD / ( resource + "_c" )
        if not src.exists():
            raise FileNotFoundError( src )
        strip_guid( src, dst )
    return dst


def cloud_texture( resource ):
    """ A cloud vtex as a PNG in the cache. """
    compiled = cloud_file( resource )
    png = compiled.with_name( compiled.name.replace( ".vtex_c", ".png" ) )
    if not png.exists():
        vrf( "-i", compiled, "-o", compiled.parent, "-d" )
    return png if png.exists() else None


def cloud_material( resource ):
    """ A compiled vmat's shader and texture and float parameters. """
    text = vrf( "-i", cloud_file( resource ), "-b", "DATA" )
    shader = re.search( r'm_shaderName = "([^"]+)"', text ).group( 1 )
    textures = dict( re.findall( r'm_name = "(\w+)"\s+m_pValue = resource:"([^"]+)"', text ) )
    values = { k: float( v ) for k, v in re.findall( r'm_name = "(\w+)"\s+m_flValue = ([-\d.e]+)', text ) }
    vectors = { k: floats( v ) for k, v in re.findall( r'm_name = "(\w+)"\s+m_value = (\[[^\]]*\])', text ) }
    return { "shader": shader, "textures": textures, "values": values, "vectors": vectors }


def cloud_model( resource ):
    """ A cloud vmdl's LOD 0 as a glb in the cache. """
    compiled = cloud_file( resource )
    glb = compiled.with_suffix( "" ).with_suffix( ".glb" )
    if not glb.exists():
        vrf( "-i", compiled, "-o", compiled.parent, "-d", "--gltf_export_format", "glb" )
    if not glb.exists():
        raise FileNotFoundError( glb )
    return glb


# ---------------------------------------------------------------------------------------------------------------------
# Materials

IMAGES = {}


def image( path, data=False ):
    """ An image by Assets path or absolute path, colour or data. None if it isn't there (or is a constant). """
    if not path or is_vector( path ):
        return None
    p = Path( path )
    if not p.is_absolute():
        p = ASSETS / path
    if not p.is_file():
        return None
    key = ( str( p ), data )
    if key not in IMAGES:
        img = bpy.data.images.load( str( p ), check_existing=False )
        img.colorspace_settings.name = "Non-Color" if data else "sRGB"
        IMAGES[key] = img
    return IMAGES[key]


def parse_vmat( path ):
    text = ( ASSETS / path ).read_text( encoding="utf-8", errors="replace" )
    shader = re.search( r'shader\s+"([^"]+)"', text ).group( 1 )
    keys = dict( re.findall( r'^\s*(\w+)\s+"([^"]*)"', text, re.M ) )
    flags = { k: int( v ) for k, v in re.findall( r'^\s*(F_\w+)\s+(\d+)', text, re.M ) }
    keys.update( { k: str( v ) for k, v in flags.items() } )
    return shader, keys


def srgb_to_linear( c ):
    return [ x / 12.92 if x <= 0.04045 else ( ( x + 0.055 ) / 1.055 ) ** 2.4 for x in c ]


class Graph:
    """ A material's node tree, built left to right. """

    def __init__( self, name ):
        self.mat = bpy.data.materials.new( name )
        self.mat.use_nodes = True
        self.nodes = self.mat.node_tree.nodes
        self.links = self.mat.node_tree.links
        self.nodes.clear()
        self.out = self.node( "ShaderNodeOutputMaterial" )

    def node( self, kind, **props ):
        n = self.nodes.new( kind )
        for k, v in props.items():
            setattr( n, k, v )
        return n

    def link( self, a, b ):
        self.links.new( a, b )

    def tex( self, img, vector=None, extension="REPEAT" ):
        n = self.node( "ShaderNodeTexImage", image=img, extension=extension )
        if vector is not None:
            self.link( vector, n.inputs["Vector"] )
        return n

    def math( self, op, a, b=None, clamp=False ):
        n = self.node( "ShaderNodeMath", operation=op, use_clamp=clamp )
        for i, v in enumerate( ( a, b ) ):
            if v is None:
                continue
            if isinstance( v, ( int, float ) ):
                n.inputs[i].default_value = float( v )
            else:
                self.link( v, n.inputs[i] )
        return n.outputs[0]

    def vmath( self, op, a, b=None ):
        n = self.node( "ShaderNodeVectorMath", operation=op )
        for i, v in enumerate( ( a, b ) ):
            if v is None:
                continue
            if isinstance( v, ( tuple, list ) ):
                n.inputs[i].default_value = tuple( float( x ) for x in v )
            else:
                self.link( v, n.inputs[i] )
        return n.outputs["Vector"] if op not in ( "DOT_PRODUCT", "LENGTH", "DISTANCE" ) else n.outputs["Value"]

    def mix( self, factor, a, b ):
        """ a where factor is 0, b where it's 1. """
        n = self.node( "ShaderNodeMix", data_type="RGBA" )
        for socket, v in ( ( n.inputs[0], factor ), ( n.inputs[6], a ), ( n.inputs[7], b ) ):
            if isinstance( v, ( int, float ) ):
                socket.default_value = float( v )
            elif isinstance( v, ( tuple, list ) ):
                socket.default_value = ( *map( float, v[:3] ), 1.0 )
            else:
                self.link( v, socket )
        return n.outputs[2]

    def finish( self, bsdf_out, visible=None ):
        """ The surface: the BSDF where visible is 1, see-through where it's 0. """
        if visible is None:
            self.link( bsdf_out, self.out.inputs["Surface"] )
            return self.mat
        clear = self.node( "ShaderNodeBsdfTransparent" )
        mix = self.node( "ShaderNodeMixShader" )
        self.link( visible, mix.inputs[0] )
        self.link( clear.outputs[0], mix.inputs[1] )
        self.link( bsdf_out, mix.inputs[2] )
        self.link( mix.outputs[0], self.out.inputs["Surface"] )
        return self.mat


def scalar_texture( g, keys, name, default ):
    """ A material's single-channel input: its texture's red channel, or the constant the vmat gives. """
    value = keys.get( name, "" )
    img = image( value, data=True )
    if img is not None:
        sep = g.node( "ShaderNodeSeparateColor" )
        g.link( g.tex( img ).outputs["Color"], sep.inputs[0] )
        return sep.outputs[0]
    if is_vector( value ):
        return floats( value )[0]
    return default


def standard_material( name, keys ):
    """ complex.shader. """
    g = Graph( name )
    p = g.node( "ShaderNodeBsdfPrincipled" )
    tint = floats( keys.get( "g_vColorTint", "[1 1 1 1]" ) )[:3]
    colour_img = image( keys.get( "TextureColor", "" ) )
    colour = g.tex( colour_img ).outputs["Color"] if colour_img else None
    if colour is None:
        base = srgb_to_linear( floats( keys["TextureColor"] )[:3] ) if is_vector( keys.get( "TextureColor", "" ) ) \
            else [ 1, 1, 1 ]
        p.inputs["Base Color"].default_value = ( *( b * t for b, t in zip( base, tint ) ), 1.0 )
    else:
        colour = g.vmath( "MULTIPLY", colour, tint )
        ao_img = image( keys.get( "TextureAmbientOcclusion", "" ), data=True )
        if ao_img is not None:
            # The engine darkens only the ambient light by it; a share of it on the albedo stands in for that.
            ao = g.tex( ao_img ).outputs["Color"]
            colour = g.mix( 0.35, colour, g.vmath( "MULTIPLY", colour, ao ) )
        g.link( colour, p.inputs["Base Color"] )
    normal_img = image( keys.get( "TextureNormal", "" ), data=True )
    if normal_img is not None:
        nm = g.node( "ShaderNodeNormalMap" )
        g.link( g.tex( normal_img ).outputs["Color"], nm.inputs["Color"] )
        g.link( nm.outputs["Normal"], p.inputs["Normal"] )
    rough = scalar_texture( g, keys, "TextureRoughness", 0.7 )
    scale = float( keys.get( "g_flRoughnessScaleFactor", "1" ) )
    if not isinstance( rough, float ) and abs( scale - 1 ) > 1e-3:
        rough = g.math( "POWER", rough, scale )
    if isinstance( rough, float ):
        p.inputs["Roughness"].default_value = rough
    else:
        g.link( rough, p.inputs["Roughness"] )
    metal = scalar_texture( g, keys, "TextureMetalness", float( keys.get( "g_flMetalness", "0" ) ) )
    if isinstance( metal, float ):
        p.inputs["Metallic"].default_value = metal
    else:
        g.link( metal, p.inputs["Metallic"] )
    visible = None
    alpha_img = image( keys.get( "TextureTranslucency", "" ), data=True )
    if keys.get( "F_ALPHA_TEST" ) == "1":
        a = g.tex( alpha_img ).outputs["Color"] if alpha_img else None
        if a is not None:
            sep = g.node( "ShaderNodeSeparateColor" )
            g.link( a, sep.inputs[0] )
            visible = g.math( "GREATER_THAN", sep.outputs[0], float( keys.get( "g_flAlphaTestReference", "0.5" ) ) )
    elif keys.get( "F_TRANSLUCENT" ) == "1":
        if alpha_img is not None:
            sep = g.node( "ShaderNodeSeparateColor" )
            g.link( g.tex( alpha_img ).outputs["Color"], sep.inputs[0] )
            g.link( sep.outputs[0], p.inputs["Alpha"] )
        else:
            p.inputs["Alpha"].default_value = 0.4
    if keys.get( "F_SELF_ILLUM" ) == "1":
        mask_img = image( keys.get( "TextureSelfIllumMask", "" ), data=True )
        glow = colour if colour is not None else p.inputs["Base Color"].default_value
        if mask_img is not None and colour is not None:
            glow = g.vmath( "MULTIPLY", colour, g.tex( mask_img ).outputs["Color"] )
        if isinstance( glow, bpy.types.NodeSocket ):
            g.link( glow, p.inputs["Emission Color"] )
        else:
            p.inputs["Emission Color"].default_value = glow
        p.inputs["Emission Strength"].default_value = float( keys.get( "g_flSelfIllumBrightness", "1" ) )
    if keys.get( "F_RENDER_BACKFACES" ) != "1":
        front = g.math( "SUBTRACT", 1.0, g.node( "ShaderNodeNewGeometry" ).outputs["Backfacing"] )
        visible = front if visible is None else g.math( "MULTIPLY", visible, front )
    return g.finish( p.outputs[0], visible )


def glass_material( name, keys ):
    """
    glass.shader as the engine composites it: what's behind shows through times the albedo and ( 1 - roughness x
    AlbedoAbsorption ), the albedo times roughness x AlbedoAbsorption is lit like a film on the pane, and the
    reflection goes as the Fresnel term.
    """
    g = Graph( name )
    colour_img = image( keys.get( "TextureColor", "" ) )
    if colour_img is not None:
        albedo = g.tex( colour_img ).outputs["Color"]
    else:
        albedo = srgb_to_linear( floats( keys.get( "TextureColor", "[1 1 1 0]" ) )[:3] )
    rough = scalar_texture( g, keys, "TextureRoughness", 0.05 )
    absorb = float( keys.get( "AlbedoAbsorption", "0" ) )
    film = g.math( "MULTIPLY", rough, absorb ) if not isinstance( rough, float ) else rough * absorb

    def scaled( share ):
        if isinstance( albedo, list ):
            if isinstance( share, float ):
                return [ a * share for a in albedo ]
            n = g.node( "ShaderNodeVectorMath", operation="SCALE" )
            n.inputs[0].default_value = tuple( albedo )
            g.link( share, n.inputs["Scale"] )
            return n.outputs["Vector"]
        n = g.node( "ShaderNodeVectorMath", operation="SCALE" )
        g.link( albedo, n.inputs[0] )
        if isinstance( share, float ):
            n.inputs["Scale"].default_value = share
        else:
            g.link( share, n.inputs["Scale"] )
        return n.outputs["Vector"]

    def colour_input( socket, value ):
        if isinstance( value, list ):
            socket.default_value = ( *value[:3], 1.0 )
        else:
            g.link( value, socket )

    through = scaled( g.math( "SUBTRACT", 1.0, film ) if not isinstance( film, float ) else 1.0 - film )
    clear = g.node( "ShaderNodeBsdfTransparent" )
    colour_input( clear.inputs["Color"], through )
    gloss = g.node( "ShaderNodeBsdfGlossy" )
    if isinstance( rough, float ):
        gloss.inputs["Roughness"].default_value = rough
    else:
        g.link( rough, gloss.inputs["Roughness"] )
    fresnel = g.node( "ShaderNodeFresnel" )
    fresnel.inputs["IOR"].default_value = 1.5
    surface = g.node( "ShaderNodeMixShader" )
    g.link( fresnel.outputs[0], surface.inputs[0] )
    g.link( clear.outputs[0], surface.inputs[1] )
    g.link( gloss.outputs[0], surface.inputs[2] )
    diffuse = g.node( "ShaderNodeBsdfDiffuse" )
    colour_input( diffuse.inputs["Color"], scaled( film ) )
    total = g.node( "ShaderNodeAddShader" )
    g.link( surface.outputs[0], total.inputs[0] )
    g.link( diffuse.outputs[0], total.inputs[1] )
    return g.finish( total.outputs[0] )


def compiled_material( name, spec ):
    """ A cloud material: complex (old packing: roughness in the normal map's alpha), foliage or bark. """
    g = Graph( name )
    p = g.node( "ShaderNodeBsdfPrincipled" )
    t = spec["textures"]
    tint = spec["vectors"].get( "g_flTintColor", spec["vectors"].get( "g_vColorTint", [ 1, 1, 1 ] ) )[:3]

    def texture( name, data=False ):
        png = cloud_texture( t[name] ) if name in t else None
        img = image( png, data ) if png else None
        if img is None:
            return None
        img.alpha_mode = "CHANNEL_PACKED"
        return g.tex( img )

    visible = None
    p.inputs["Roughness"].default_value = 0.8
    ct = texture( "g_tColor" )
    if ct:
        colour = g.vmath( "MULTIPLY", ct.outputs["Color"], tint )
        at = texture( "g_tAmbientOcclusion", True )
        if at:
            colour = g.mix( 0.35, colour, g.vmath( "MULTIPLY", colour, at.outputs["Color"] ) )
        g.link( colour, p.inputs["Base Color"] )
        if "foliage" in spec["shader"]:
            visible = g.math( "GREATER_THAN", ct.outputs["Alpha"], spec["values"].get( "g_flAlphaTestReference", 0.5 ) )
    nt = texture( "g_tNormal", True )
    if nt:
        nm = g.node( "ShaderNodeNormalMap" )
        g.link( nt.outputs["Color"], nm.inputs["Color"] )
        g.link( nm.outputs["Normal"], p.inputs["Normal"] )
        if "g_tRma" not in t and "complex" in spec["shader"]:
            g.link( nt.outputs["Alpha"], p.inputs["Roughness"] )
    rt = texture( "g_tRma", True )
    if rt:
        sep = g.node( "ShaderNodeSeparateColor" )
        g.link( rt.outputs["Color"], sep.inputs[0] )
        floor = spec["values"].get( "g_flMinRoughness", 0.0 )
        g.link( g.math( "MAXIMUM", sep.outputs[0], floor ), p.inputs["Roughness"] )
    if "g_tTransmissiveColor" in t and texture( "g_tTransmissiveColor" ):
        # Leaves let light through: a share of a translucent BSDF in the leaves' transmitted colour.
        tr = g.node( "ShaderNodeBsdfTranslucent" )
        g.link( texture( "g_tTransmissiveColor" ).outputs["Color"], tr.inputs["Color"] )
        mix = g.node( "ShaderNodeMixShader" )
        mix.inputs[0].default_value = 0.3
        g.link( p.outputs[0], mix.inputs[1] )
        g.link( tr.outputs[0], mix.inputs[2] )
        return g.finish( mix.outputs[0], visible )
    return g.finish( p.outputs[0], visible )


MATERIALS = {}


def material( path ):
    """ The material for a vmat path. """
    if path in MATERIALS:
        return MATERIALS[path]
    try:
        if ( ASSETS / path ).is_file():
            shader, keys = parse_vmat( path )
            if "glass" in shader:
                mat = glass_material( path, keys )
            else:
                mat = standard_material( path, keys )
        else:
            mat = compiled_material( path, cloud_material( path ) )
    except Exception as error:
        # Magenta, so a material it couldn't build shows.
        print( f"  {path}: {type( error ).__name__}: {error}" )
        g = Graph( path )
        p = g.node( "ShaderNodeBsdfPrincipled" )
        p.inputs["Base Color"].default_value = ( 0.8, 0.0, 0.8, 1.0 )
        mat = g.finish( p.outputs[0] )
    MATERIALS[path] = mat
    return mat


# ---------------------------------------------------------------------------------------------------------------------
# Models

def map_model( path ):
    """ A map vmdl: its OBJ imported unturned, with the remapped materials. Place it with world @ OBJ_TO_MODEL. """
    text = ( ASSETS / path ).read_text( encoding="utf-8" )
    obj = ASSETS / re.search( r'filename = "([^"]+\.obj)"', text ).group( 1 )
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
            else:
                print( f"  {path}: no remap for {mtl}" )
    return objects


def gltf_meshes( glb ):
    """ The primitives of a Source2Viewer glb as ( positions, normals, uvs, triangles ), in s&box units and axes. """
    data = Path( glb ).read_bytes()
    n = struct.unpack_from( "<I", data, 12 )[0]
    j = json.loads( data[20:20 + n] )
    binary = data[20 + n + 8:]
    sizes = { "SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4 }
    kinds = { 5126: np.float32, 5125: np.uint32, 5123: np.uint16 }

    def accessor( i ):
        a = j["accessors"][i]
        view = j["bufferViews"][a["bufferView"]]
        dtype = kinds[a["componentType"]]
        count = a["count"] * sizes[a["type"]]
        start = view.get( "byteOffset", 0 ) + a.get( "byteOffset", 0 )
        stride = view.get( "byteStride" )
        width = sizes[a["type"]]
        if stride and stride != width * np.dtype( dtype ).itemsize:
            raw = np.frombuffer( binary, np.uint8, a["count"] * stride, start ).reshape( a["count"], stride )
            return raw[:, :width * np.dtype( dtype ).itemsize].copy().view( dtype ).reshape( a["count"], width )
        return np.frombuffer( binary, dtype, count, start ).reshape( a["count"], width ) if width > 1 else \
            np.frombuffer( binary, dtype, count, start )

    out = []
    for prim in j["meshes"][0]["primitives"]:
        at = prim["attributes"]
        pos = accessor( at["POSITION"] ).astype( float )
        nrm = accessor( at["NORMAL"] ).astype( float )
        uv = accessor( at["TEXCOORD_0"] ).astype( float )
        tri = accessor( prim["indices"] ).astype( np.int64 ).reshape( -1, 3 )
        # Source2Viewer writes s&box ( x, y, z ) inches as glTF ( y, z, x ) metres, baked into the vertices.
        pos = np.stack( ( pos[:, 2], pos[:, 0], pos[:, 1] ), 1 ) * GLTF_UNITS
        nrm = np.stack( ( nrm[:, 2], nrm[:, 0], nrm[:, 1] ), 1 )
        uv = np.stack( ( uv[:, 0], 1.0 - uv[:, 1] ), 1 )
        out.append( ( pos, nrm, uv, tri ) )
    return out


def mesh_object( name, pos, nrm, uv, tri, mat ):
    me = bpy.data.meshes.new( name )
    me.vertices.add( len( pos ) )
    me.vertices.foreach_set( "co", pos.astype( np.float32 ).ravel() )
    me.loops.add( tri.size )
    me.loops.foreach_set( "vertex_index", tri.astype( np.int32 ).ravel() )
    me.polygons.add( len( tri ) )
    me.polygons.foreach_set( "loop_start", ( np.arange( len( tri ) ) * 3 ).astype( np.int32 ) )
    me.polygons.foreach_set( "loop_total", np.full( len( tri ), 3, np.int32 ) )
    layer = me.uv_layers.new( name="UVMap" )
    layer.data.foreach_set( "uv", uv[tri.ravel()].astype( np.float32 ).ravel() )
    me.update()
    me.validate()
    me.normals_split_custom_set_from_vertices( [ tuple( v ) for v in nrm ] )
    me.polygons.foreach_set( "use_smooth", np.ones( len( tri ), bool ) )
    me.materials.append( mat )
    return bpy.data.objects.new( name, me )


# The materials of each cloud model's LOD 0 primitives, in the glb's order. The oaks' first primitive is the trunk and
# boughs, the second the leaf cards.
CLOUD_PRIMITIVES = {
    "models/sbox_props/trees/oak/tree_oak_small_a.vmdl":
        ( "models/sbox_props/trees/oak/oak_bark.vmat", "models/sbox_props/trees/oak/oak_branch.vmat" ),
    "models/sbox_props/trees/oak/tree_oak_medium_a.vmdl":
        ( "models/sbox_props/trees/oak/oak_bark.vmat", "models/sbox_props/trees/oak/oak_branch.vmat" ),
    "models/sbox_props/shrubs/beech/beech_bush_small.vmdl": ( "models/sbox_props/shrubs/beech/beech_shrub.vmat", ),
}


def cloud_prop( path ):
    """ A cloud model as a collection to instance: its LOD 0 primitives with their materials. """
    glb = cloud_model( path )
    coll = bpy.data.collections.new( Path( path ).stem )
    meshes = gltf_meshes( glb )
    mats = CLOUD_PRIMITIVES.get( path )
    if mats is None or len( mats ) != len( meshes ):
        raise KeyError( f"{path}: add its {len( meshes )} primitives' materials to CLOUD_PRIMITIVES" )
    for i, ( ( pos, nrm, uv, tri ), vmat ) in enumerate( zip( meshes, mats ) ):
        coll.objects.link( mesh_object( f"{coll.name}_{i}", pos, nrm, uv, tri, material( vmat ) ) )
    return coll


# ---------------------------------------------------------------------------------------------------------------------
# Lights, sky, fog and camera

def add_sun( world, colour ):
    strength = max( colour[:3] )
    light = bpy.data.lights.new( "Sun", "SUN" )
    light.color = tuple( c / strength for c in colour[:3] )
    # An engine light's colour is the radiance a white surface facing it shows; Cycles' strength is irradiance.
    light.energy = math.pi * strength
    light.angle = math.radians( 0.53 )
    obj = bpy.data.objects.new( "Sun", light )
    forward = world.to_3x3() @ Vector( ( 1, 0, 0 ) )
    obj.rotation_euler = forward.to_track_quat( "-Z", "Y" ).to_euler()
    bpy.context.scene.collection.objects.link( obj )
    return forward


def add_point( world, colour, radius ):
    strength = max( max( colour[:3] ), 1e-3 )
    light = bpy.data.lights.new( "Point", "POINT" )
    light.color = tuple( c / strength for c in colour[:3] )
    # Bright as the engine's colour a quarter of its radius out, falling off with the square of the distance.
    d0 = radius / 4
    light.energy = 4 * math.pi * d0 * d0 * math.pi * strength
    light.shadow_soft_size = 4.0
    obj = bpy.data.objects.new( "Point", light )
    obj.location = world.to_translation()
    bpy.context.scene.collection.objects.link( obj )


def add_sky( material_path, haze ):
    _, keys = parse_vmat( material_path )
    world = bpy.data.worlds.new( "Sky" )
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    nodes.clear()
    coords = nodes.new( "ShaderNodeTexCoord" )
    mapping = nodes.new( "ShaderNodeMapping" )
    # s&box's u is -azimuth / 2 pi (belltower_sky.U_SIGN); Blender's is 0.5 - azimuth / 2 pi: half a turn apart.
    mapping.inputs["Rotation"].default_value = ( 0.0, 0.0, math.pi )
    env = nodes.new( "ShaderNodeTexEnvironment" )
    env.image = image( keys["SkyTexture"], data=False )
    env.image.colorspace_settings.name = "Linear Rec.709"
    background = nodes.new( "ShaderNodeBackground" )
    background.inputs["Strength"].default_value = 2 ** float( keys.get( "g_flBrightnessExposureBias", "0" ) )
    output = nodes.new( "ShaderNodeOutputWorld" )
    links.new( coords.outputs["Generated"], mapping.inputs["Vector"] )
    links.new( mapping.outputs["Vector"], env.inputs["Vector"] )
    links.new( env.outputs["Color"], background.inputs["Color"] )
    links.new( background.outputs["Background"], output.inputs["Surface"] )
    if haze > 0:
        # A thin, faintly warm medium everywhere, for the sun's shafts through the roof.
        scatter = nodes.new( "ShaderNodeVolumeScatter" )
        scatter.inputs["Density"].default_value = haze
        scatter.inputs["Anisotropy"].default_value = 0.55
        scatter.inputs["Color"].default_value = ( 1.0, 0.97, 0.92, 1.0 )
        links.new( scatter.outputs[0], output.inputs["Volume"] )
    bpy.context.scene.world = world


# A VolumetricFogVolume's Strength as a scattering density per inch. A guess at the engine's own scale, to tune
# against a match.
FOG_VOLUME_DENSITY = 0.0004


def add_fog_volume( world, c ):
    bounds = c.get( "Bounds", {} )
    lo = Vector( floats( bounds.get( "Mins", "-50,-50,-50" ) ) )
    hi = Vector( floats( bounds.get( "Maxs", "50,50,50" ) ) )
    bpy.ops.mesh.primitive_cube_add( size=1.0 )
    cube = bpy.context.active_object
    cube.name = "FogVolume"
    cube.matrix_world = world @ Matrix.Translation( ( lo + hi ) / 2 ) @ Matrix.Diagonal( ( *( hi - lo ), 1.0 ) )
    g = Graph( "FogVolume" )
    v = g.node( "ShaderNodeVolumePrincipled" )
    colour = floats( c.get( "Color", "1,1,1,1" ) )
    v.inputs["Color"].default_value = ( *colour[:3], 1.0 )
    v.inputs["Density"].default_value = float( c.get( "Strength", 1 ) ) * FOG_VOLUME_DENSITY
    v.inputs["Anisotropy"].default_value = 0.5
    g.link( v.outputs[0], g.out.inputs["Volume"] )
    cube.data.materials.append( g.mat )


def plan_to_world( p ):
    e, n, z = p
    return Vector( ( n, -e, z ) )


def set_camera( eye, target, fov ):
    cam = bpy.context.scene.camera
    if cam is None:
        data = bpy.data.cameras.new( "Camera" )
        cam = bpy.data.objects.new( "Camera", data )
        bpy.context.scene.collection.objects.link( cam )
        bpy.context.scene.camera = cam
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.angle_x = math.radians( fov )
    cam.data.clip_start = 2.0
    cam.data.clip_end = 400000.0
    cam.location = plan_to_world( eye )
    direction = plan_to_world( target ) - cam.location
    cam.rotation_euler = direction.to_track_quat( "-Z", "Y" ).to_euler()
    return cam


# ---------------------------------------------------------------------------------------------------------------------
# How a match shows it

def aces( rgb ):
    v = rgb @ ACES_IN
    a = v * ( v + 0.0245786 ) - 0.000090537
    b = v * ( 0.983729 * v + 0.4329510 ) + 0.238081
    return np.clip( ( a / b ) @ ACES_OUT, 0, 1 )


def kelvin_rgb( k ):
    """ A black body's colour (Tanner Helland's fit), linear, normalised to its largest channel. """
    t = k / 100.0
    r = 255.0 if t <= 66 else 329.698727446 * ( t - 60 ) ** -0.1332047592
    g = 99.4708025861 * math.log( t ) - 161.1195681661 if t <= 66 else 288.1221695283 * ( t - 60 ) ** -0.0755148492
    b = 255.0 if t >= 66 else ( 0.0 if t <= 19 else 138.5177312231 * math.log( t - 10 ) - 305.0447927307 )
    c = np.clip( np.array( ( r, g, b ) ) / 255.0, 0, 1 )
    c = np.where( c <= 0.04045, c / 12.92, ( ( c + 0.055 ) / 1.055 ) ** 2.4 )
    return c / c.max()


def read_layers( path ):
    """ Every pass in a multilayer EXR. Blender 5 writes each pass as a part of its own (an OIIO subimage), so
    the first part is only the beauty pass. """
    import OpenImageIO as oiio
    inp = oiio.ImageInput.open( str( path ) )
    parts = []
    index = 0
    while inp.seek_subimage( index, 0 ):
        names = list( inp.spec().channelnames )
        parts.append( ( names, inp.read_image( 0, 0, 0, len( names ), oiio.FLOAT ) ) )
        index += 1
    inp.close()

    def channels( *wanted ):
        columns = []
        for w in wanted:
            hits = [ ( pixels, i ) for names, pixels in parts for i, n in enumerate( names ) if n.endswith( w ) ]
            if not hits:
                raise KeyError( f"{w} not in {[ n for names, _ in parts for n in names ]}" )
            pixels, i = hits[0]
            columns.append( pixels[..., i] )
        return np.stack( columns, axis=-1 )

    return channels


def blur( img, radius ):
    """ A separable Gaussian blur of an ( h, w, 3 ) image, radius in pixels. """
    if radius < 0.5:
        return img
    r = int( math.ceil( radius * 3 ) )
    x = np.arange( -r, r + 1 )
    k = np.exp( -0.5 * ( x / radius ) ** 2 )
    k /= k.sum()
    out = img
    for axis in ( 0, 1 ):
        pad = [ ( 0, 0 ) ] * 3
        pad[axis] = ( r, r )
        padded = np.pad( out, pad, mode="edge" )
        acc = np.zeros_like( out )
        for i, w in enumerate( k ):
            sl = [ slice( None ) ] * 3
            sl[axis] = slice( i, i + out.shape[axis] )
            acc += w * padded[tuple( sl )]
        out = acc
    return out


def bloom( rgb, strength, threshold=1.0 ):
    """ A wide glow round what's brighter than the threshold: blurs over a chain of halvings, summed. """
    bright = np.maximum( rgb - threshold, 0 )
    h, w = rgb.shape[:2]
    glow = np.zeros_like( rgb )
    level = bright
    weights = ( 0.3, 0.25, 0.2, 0.15, 0.1 )
    for i, weight in enumerate( weights ):
        level = blur( level, 1.5 )
        if i:
            level = level[: level.shape[0] // 2 * 2, : level.shape[1] // 2 * 2]
            level = 0.25 * ( level[0::2, 0::2] + level[1::2, 0::2] + level[0::2, 1::2] + level[1::2, 1::2] )
        scale = 2 ** i
        up = np.repeat( np.repeat( level, scale, 0 ), scale, 1 )
        up = np.pad( up, ( ( 0, max( 0, h - up.shape[0] ) ), ( 0, max( 0, w - up.shape[1] ) ), ( 0, 0 ) ), mode="edge" )
        glow += weight * blur( up[:h, :w], scale * 0.75 )
    return rgb + strength * glow


def finish_view( exr, png, cam_pos, fog, look, exposure, glow ):
    """ Fog, exposure, bloom, ACES, the colour temperature and the vignette, as the scene's Look volume shows it. """
    import OpenImageIO as oiio
    layers = read_layers( exr )
    rgb = layers( "Combined.R", "Combined.G", "Combined.B" ).astype( float )
    pos = layers( "Position.X", "Position.Y", "Position.Z" ).astype( float )
    depth = layers( "Depth.Z" )[..., 0]
    hit = depth < 1e9
    if fog is not None:
        colour = np.array( floats( fog["Color"] )[:3] )
        alpha = floats( fog["Color"] )[3]
        start, end = float( fog["StartDistance"] ), float( fog["EndDistance"] )
        dist = np.linalg.norm( pos - np.array( cam_pos ), axis=-1 )
        along = np.clip( ( dist - start ) / ( end - start ), 0, 1 ) ** float( fog["FalloffExponent"] )
        height = np.clip( 1 - pos[..., 2] / float( fog["Height"] ), 0, 1 ) ** float( fog.get( "VerticalFalloffExponent", 1 ) )
        amount = np.where( hit, alpha * along * height, 0.0 )[..., None]
        rgb = rgb * ( 1 - amount ) + colour * amount
    lit = np.maximum( rgb, 0 ) * exposure
    if glow > 0:
        lit = bloom( lit, glow )
    out = aces( lit )
    grading = look.get( "ColorGrading" )
    if grading and grading.get( "GradingMethod" ) == "TemperatureControl":
        tint = kelvin_rgb( float( grading.get( "ColorTempK", 6500 ) ) ) / kelvin_rgb( 6500 )
        tint = tint / tint.max()
        out = out * ( 1 + ( tint - 1 ) * float( grading.get( "BlendFactor", 1 ) ) )
    vignette = look.get( "Vignette" )
    if vignette:
        h, w = out.shape[:2]
        ys, xs = np.mgrid[0:h, 0:w]
        r = np.hypot( ( xs + 0.5 ) / w - 0.5, ( ( ys + 0.5 ) / h - 0.5 ) * h / w ) / math.hypot( 0.5, 0.5 * h / w )
        out = out * ( 1 - float( vignette.get( "Intensity", 0 ) ) * np.clip( r, 0, 1 ) ** 2 )[..., None]
    out = np.clip( out, 0, 1 )
    out = np.where( out <= 0.0031308, 12.92 * out, 1.055 * np.power( out, 1 / 2.4 ) - 0.055 )
    image8 = np.clip( np.rint( out * 255 ), 0, 255 ).astype( np.uint8 )
    spec = oiio.ImageSpec( image8.shape[1], image8.shape[0], 3, oiio.UINT8 )
    buf = oiio.ImageBuf( spec )
    buf.set_pixels( oiio.ROI(), image8 )
    buf.write( str( png ) )


# ---------------------------------------------------------------------------------------------------------------------

def parse_args():
    argv = sys.argv[sys.argv.index( "--" ) + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser( prog="railhead_render.py" )
    ap.add_argument( "--views", default="reference" )
    ap.add_argument( "--view", action="append", default=[], help="name,e,n,z,te,tn,tz,fov" )
    ap.add_argument( "--size", default="1280x720" )
    ap.add_argument( "--samples", type=int, default=64 )
    ap.add_argument( "--bounces", type=int, default=2 )
    ap.add_argument( "--out", default=str( TEMP / "renders" ) )
    ap.add_argument( "--cpu", action="store_true" )
    ap.add_argument( "--threads", type=int, default=0, help="CPU threads (0: all)" )
    ap.add_argument( "--no-trees", action="store_true" )
    ap.add_argument( "--texture-limit", default="2048" )
    ap.add_argument( "--exposure", type=float, default=None )
    ap.add_argument( "--haze", type=float, default=0.0, help="scattering per inch everywhere (0: none)" )
    ap.add_argument( "--bloom", type=float, default=0.0, help="glow strength round the brightest light (0: none)" )
    ap.add_argument( "--rerender", action="store_true", help="only redo the PNGs from the EXRs already written" )
    return ap.parse_args( argv )


def main():
    args = parse_args()
    started = time.time()
    views = { v[0]: v for v in literal( ROOT / "Tools/railhead_preview.py", "VIEWS" ) + REFERENCE_VIEWS }
    wanted = [ views[name] for name in args.views.split( "," ) if name ] if args.views != "all" else list( views.values() )
    for custom in args.view:
        parts = custom.split( "," )
        nums = [ float( x ) for x in parts[1:] ]
        wanted.append( ( parts[0], tuple( nums[0:3] ), tuple( nums[3:6] ), nums[6] if len( nums ) > 6 else 80 ) )
    exposure = args.exposure or literal( ROOT / "Tools/railhead_map.py", "SKY_EXPOSURE" )
    out = Path( args.out )
    out.mkdir( parents=True, exist_ok=True )

    bpy.ops.wm.read_factory_settings( use_empty=True )
    scene = bpy.context.scene
    found = read_scene()
    if args.rerender:
        for name, eye, target, fov in wanted:
            finish_view( out / f"{name}.exr", out / f"{name}.png", tuple( plan_to_world( eye ) ), found["fog"],
                         found["look"], exposure, args.bloom )
            print( f"{name}: -> {out / ( name + '.png' )}" )
        return

    placed = {}
    for path, world, tint in found["models"]:
        if path.startswith( "models/maps/" ):
            if path in placed:
                # Placed again: more objects on the same meshes.
                copies = [ o.copy() for o in placed[path] ]
                for o in copies:
                    scene.collection.objects.link( o )
            else:
                copies = placed[path] = map_model( path )
                print( f"{path}: {sum( len( o.data.polygons ) for o in copies )} faces" )
            for o in copies:
                o.matrix_world = world @ OBJ_TO_MODEL
        elif not args.no_trees:
            if path not in placed:
                placed[path] = cloud_prop( path )
            empty = bpy.data.objects.new( Path( path ).stem, None )
            empty.instance_type = "COLLECTION"
            empty.instance_collection = placed[path]
            empty.matrix_world = world
            scene.collection.objects.link( empty )
    for world, colour in found["suns"]:
        add_sun( world, colour )
    for world, colour, radius in found["points"]:
        add_point( world, colour, radius )
    for world, c in found["volumes"]:
        add_fog_volume( world, c )
    if found["sky"]:
        add_sky( found["sky"][0], args.haze )
    print( f"scene built in {time.time() - started:.0f} s" )

    w, h = ( int( x ) for x in args.size.split( "x" ) )
    scene.render.engine = "CYCLES"
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = args.bounces
    scene.cycles.glossy_bounces = 2
    scene.cycles.transparent_max_bounces = 16
    scene.cycles.volume_bounces = 1
    scene.cycles.volume_step_rate = 4.0
    scene.cycles.texture_limit_render = args.texture_limit
    scene.render.use_simplify = True
    if args.threads:
        scene.render.threads_mode = "FIXED"
        scene.render.threads = args.threads
    if not args.cpu:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ( "OPTIX", "CUDA" ):
            try:
                prefs.compute_device_type = kind
                prefs.get_devices()
                gpus = [ d for d in prefs.devices if d.type == kind ]
                if gpus:
                    for d in prefs.devices:
                        d.use = d.type == kind
                    scene.cycles.device = "GPU"
                    print( f"rendering on {kind}: {', '.join( d.name for d in gpus )}" )
                    break
            except TypeError:
                continue
    layer = scene.view_layers[0]
    layer.use_pass_z = True
    layer.use_pass_position = True
    fmt = scene.render.image_settings
    fmt.media_type = "MULTI_LAYER_IMAGE"
    fmt.file_format = "OPEN_EXR_MULTILAYER"
    fmt.color_depth = "32"
    fmt.exr_codec = "ZIP"

    for name, eye, target, fov in wanted:
        cam = set_camera( eye, target, fov )
        exr = out / f"{name}.exr"
        scene.render.filepath = str( exr )
        t0 = time.time()
        bpy.ops.render.render( write_still=True )
        finish_view( exr, out / f"{name}.png", tuple( cam.location ), found["fog"], found["look"], exposure, args.bloom )
        print( f"{name}: {time.time() - t0:.0f} s -> {out / ( name + '.png' )}" )


if __name__ == "__main__":
    main()
