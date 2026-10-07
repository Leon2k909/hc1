"""
Belltower rendered offline in Cycles, to judge its textures, colours and shapes without the editor.

    blender -b --factory-startup --python Tools/belltower_render.py -- [--views square,west_road] [--size 1280x720]
        [--samples 64] [--out <dir>] [--cpu] [--threads N] [--no-trees] [--no-vista] [--texture-limit 2048] [--exposure 2.0]
        [--view name,e,n,z,te,tn,tz,fov ...]

It reads Assets/scenes/maps/Belltower/belltower.scene as the game does:
- Every ModelRenderer. The map's own models come from their OBJs and their vmdls' remaps. The cloud oaks and beech
  bushes come from the local cloud cache (.sbox/cloud), exported once with Source2Viewer-CLI (VRF_CLI, or
  D:/tmp/hc1-mw22-tools/vrf) into the cache folder.
- The materials from their vmats:
  - complex.shader's colour, normal, roughness, AO, metalness, alpha test, translucency and self-illumination, with
    the backs of single-sided faces see-through, as the engine culls them;
  - blendable.shader's first layer;
  - hc1_vista.shader's zones, without its close-up detail.
- The sun, the point lights and the sky panorama, turned as s&box wraps it round the world.
- The Look volume: s&box's ACES at belltower_sky.DESIGN_EXPOSURE, the gradient fog, the colour temperature and the
  vignette, applied to the linear render.

What it can't show as a match does:
- Cycles bounces light (--bounces), where the engine has only the sky's ambient light and SSAO, so shaded streets come
  out warmer and lighter than in a match.
- Alpha-blended glass and water are approximations.
- There are no particles, decal components, players or bots.

The views are belltower_map.VIEWS: ( name, plan eye, plan target, horizontal fov ), with plan ( east, north, z ) at
world ( north, -east, z ). --view adds one of your own. Each is written as <name>.png, with the linear render as
<name>.exr, to --out (default: the system temp folder's hc1_belltower_render/renders).
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
SCENE = ASSETS / "scenes/maps/Belltower/belltower.scene"
TEMP = Path( tempfile.gettempdir() ) / "hc1_belltower_render"
CACHE = TEMP / "cache"
VRF_CLI = Path( os.environ.get( "VRF_CLI", "D:/tmp/hc1-mw22-tools/vrf/Source2Viewer-CLI.exe" ) )

# OBJ ( a, b, c ) is model ( y, z, x ): ModelDoc reads an OBJ as Y-up (map_kit.obj_vector).
OBJ_TO_MODEL = Matrix( ( ( 0, 0, 1, 0 ), ( 1, 0, 0, 0 ), ( 0, 1, 0, 0 ), ( 0, 0, 0, 1 ) ) )
# glTF from Source2Viewer: metres, Y up.
GLTF_UNITS = 1.0 / 0.0254

# s&box's ACES (Hill's fit), as belltower_sky.py has it.
ACES_IN = np.array( ( ( 0.59719, 0.07600, 0.02840 ), ( 0.35458, 0.90834, 0.13383 ), ( 0.04823, 0.01566, 0.83777 ) ) )
ACES_OUT = np.array( ( ( 1.60475, -0.10208, -0.00327 ), ( -0.53108, 1.10813, -0.07276 ),
                       ( -0.07367, -0.00605, 1.07602 ) ) )


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
    found = { "models": [], "suns": [], "points": [], "sky": None, "fog": None, "look": {} }

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
            elif kind == "Sandbox.SkyBox2D":
                found["sky"] = ( c.get( "SkyMaterial" ), floats( c.get( "Tint", "1,1,1,1" ) ) )
            elif kind == "Sandbox.GradientFog":
                found["fog"] = c
            elif kind in ( "Sandbox.Tonemapping", "Sandbox.ColorGrading", "Sandbox.Vignette" ):
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


def cloud_file( resource ):
    """ A compiled cloud resource ( e.g. 'models/x.vmdl' ), GUID stripped, in the cache. """
    src = CLOUD / ( resource + "_c" )
    dst = CACHE / "cloud" / ( resource + "_c" )
    if not dst.exists():
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
    """ An image by Assets path or absolute path, colour or data. None if it isn't there. """
    if not path:
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


def standard_material( name, keys, suffix="" ):
    """ complex.shader (and blendable.shader's layer A, suffix 'A'). """
    g = Graph( name )
    p = g.node( "ShaderNodeBsdfPrincipled" )
    tint = floats( keys.get( "g_vColorTint", "[1 1 1 1]" ) )[:3]
    colour_img = image( keys.get( "TextureColor" + suffix, "" ) )
    colour = g.tex( colour_img ).outputs["Color"] if colour_img else None
    if colour is None:
        p.inputs["Base Color"].default_value = ( *tint, 1.0 )
    else:
        colour = g.vmath( "MULTIPLY", colour, tint )
        ao_img = image( keys.get( "TextureAmbientOcclusion" + suffix, "" ), data=True )
        if ao_img is not None:
            # The engine darkens only the ambient light by it; a share of it on the albedo stands in for that.
            ao = g.tex( ao_img ).outputs["Color"]
            colour = g.mix( 0.35, colour, g.vmath( "MULTIPLY", colour, ao ) )
        g.link( colour, p.inputs["Base Color"] )
    normal_img = image( keys.get( "TextureNormal" + suffix, "" ), data=True )
    if normal_img is not None:
        nm = g.node( "ShaderNodeNormalMap" )
        g.link( g.tex( normal_img ).outputs["Color"], nm.inputs["Color"] )
        g.link( nm.outputs["Normal"], p.inputs["Normal"] )
    rough_img = image( keys.get( "TextureRoughness" + suffix, "" ), data=True )
    if rough_img is not None:
        r = g.tex( rough_img ).outputs["Color"]
        sep = g.node( "ShaderNodeSeparateColor" )
        g.link( r, sep.inputs[0] )
        rough = sep.outputs[0]
        scale = float( keys.get( "g_flRoughnessScaleFactor", "1" ) )
        if abs( scale - 1 ) > 1e-3:
            rough = g.math( "POWER", rough, scale )
        g.link( rough, p.inputs["Roughness"] )
    else:
        p.inputs["Roughness"].default_value = 0.7
    p.inputs["Metallic"].default_value = float( keys.get( "g_flMetalness", "0" ) )
    visible = None
    alpha_img = image( keys.get( "TextureTranslucency" + suffix, "" ), data=True )
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
        p.inputs["Emission Strength"].default_value = float( keys.get( "g_flSelfIllumBrightness", "1" ) )
    if keys.get( "F_RENDER_BACKFACES" ) != "1":
        front = g.math( "SUBTRACT", 1.0, g.node( "ShaderNodeNewGeometry" ).outputs["Backfacing"] )
        visible = front if visible is None else g.math( "MULTIPLY", visible, front )
    return g.finish( p.outputs[0], visible )


def water_material( name, keys ):
    g = Graph( name )
    p = g.node( "ShaderNodeBsdfPrincipled" )
    p.inputs["Base Color"].default_value = ( *floats( keys.get( "g_vWaterColor", "[0.1 0.2 0.2]" ) )[:3], 1.0 )
    p.inputs["Roughness"].default_value = 0.04
    p.inputs["IOR"].default_value = 1.33
    p.inputs["Alpha"].default_value = float( keys.get( "g_flWaterOpacity", "0.6" ) )
    return g.finish( p.outputs[0] )


def smoothstep( g, x, lo, hi ):
    n = g.node( "ShaderNodeMapRange", interpolation_type="SMOOTHSTEP", clamp=True )
    g.link( x, n.inputs["Value"] )
    n.inputs["From Min"].default_value = lo
    n.inputs["From Max"].default_value = hi
    return n.outputs["Result"]


def vista_material( name, keys, near_detail=False ):
    """ hc1_vista.shader: four zones round the town, picked by how far out a point is (Chebyshev). """
    g = Graph( name )
    west, east, south, north = floats( keys["g_vTown"] )
    margins = floats( keys["g_vZoneMargins"] )
    blend = float( keys["g_flZoneBlend"] )
    rough = floats( keys["g_vRoughness"] )
    pos = g.node( "ShaderNodeNewGeometry" ).outputs["Position"]
    sep = g.node( "ShaderNodeSeparateXYZ" )
    g.link( pos, sep.inputs[0] )
    plan_n = sep.outputs["X"]
    plan_e = g.math( "MULTIPLY", sep.outputs["Y"], -1.0 )
    out_e = g.math( "MAXIMUM", g.math( "MAXIMUM", g.math( "SUBTRACT", west, plan_e ), g.math( "SUBTRACT", plan_e, east ) ), 0.0 )
    out_n = g.math( "MAXIMUM", g.math( "MAXIMUM", g.math( "SUBTRACT", south, plan_n ), g.math( "SUBTRACT", plan_n, north ) ), 0.0 )
    out = g.math( "MAXIMUM", out_e, out_n )
    keep = [ g.math( "SUBTRACT", 1.0, smoothstep( g, out, m * ( 1 - blend ), m ) ) for m in margins[:3] ]
    shares = []
    rest = None
    for k in keep:
        shares.append( k if rest is None else g.math( "MULTIPLY", rest, k ) )
        left = g.math( "SUBTRACT", 1.0, k )
        rest = left if rest is None else g.math( "MULTIPLY", rest, left )
    shares.append( rest )
    colour = kind = packed = None
    for zone, margin, share in zip( "ABCD", margins, shares ):
        # u east from the zone's west edge, v (picture rows) south from its north edge; Blender's v runs up.
        size_e = ( east - west ) + 2 * margin
        size_n = ( north - south ) + 2 * margin
        u = g.math( "DIVIDE", g.math( "SUBTRACT", plan_e, west - margin ), size_e )
        v_up = g.math( "DIVIDE", g.math( "SUBTRACT", plan_n, south - margin ), size_n )
        uv = g.node( "ShaderNodeCombineXYZ" )
        g.link( u, uv.inputs[0] )
        g.link( v_up, uv.inputs[1] )
        c = g.tex( image( keys["Color" + zone] ), uv.outputs[0], "EXTEND" ).outputs["Color"]
        k = g.tex( image( keys["Kind" + zone], data=True ), uv.outputs[0], "EXTEND" ).outputs["Color"]
        n = g.tex( image( keys["Normal" + zone], data=True ), uv.outputs[0], "EXTEND" ).outputs["Color"]
        c, k, n = ( g.vmath( "SCALE", x, None ) for x in ( c, k, n ) )
        for x in ( c, k, n ):
            g.link( share, x.node.inputs["Scale"] )
        colour = c if colour is None else g.vmath( "ADD", colour, c )
        kind = k if kind is None else g.vmath( "ADD", kind, k )
        packed = n if packed is None else g.vmath( "ADD", packed, n )
    # The plan normal ( east, north, up ) to the world's ( north, -east, up ).
    psep = g.node( "ShaderNodeSeparateXYZ" )
    g.link( packed, psep.inputs[0] )
    te = g.math( "SUBTRACT", g.math( "MULTIPLY", psep.outputs[0], 2.0 ), 1.0 )
    tn = g.math( "SUBTRACT", g.math( "MULTIPLY", psep.outputs[1], 2.0 ), 1.0 )
    up = g.math( "SQRT", g.math( "MAXIMUM", g.math( "SUBTRACT", 1.0, g.math( "ADD", g.math( "MULTIPLY", te, te ), g.math( "MULTIPLY", tn, tn ) ) ), 0.0 ) )
    wn = g.node( "ShaderNodeCombineXYZ" )
    g.link( tn, wn.inputs[0] )
    g.link( g.math( "MULTIPLY", te, -1.0 ), wn.inputs[1] )
    g.link( up, wn.inputs[2] )
    # The kind: 0 grass, 1/3 soil, 2/3 stone, 1 water.
    ksep = g.node( "ShaderNodeSeparateXYZ" )
    g.link( kind, ksep.inputs[0] )
    k3 = g.math( "MULTIPLY", ksep.outputs[0], 3.0 )
    weights = [ g.math( "MAXIMUM", g.math( "SUBTRACT", 1.0, g.math( "ABSOLUTE", g.math( "SUBTRACT", k3, float( i ) ) ) ), 0.0 ) for i in range( 4 ) ]
    total = g.math( "MAXIMUM", g.math( "ADD", g.math( "ADD", weights[0], weights[1] ), g.math( "ADD", weights[2], weights[3] ) ), 1e-4 )
    r = None
    for w, value in zip( weights, rough ):
        term = g.math( "MULTIPLY", w, value )
        r = term if r is None else g.math( "ADD", r, term )
    p = g.node( "ShaderNodeBsdfPrincipled" )
    g.link( colour, p.inputs["Base Color"] )
    g.link( g.vmath( "NORMALIZE", wn.outputs[0] ), p.inputs["Normal"] )
    g.link( g.math( "DIVIDE", r, total ), p.inputs["Roughness"] )
    return g.finish( p.outputs[0] )


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
            if "hc1_vista" in shader:
                mat = vista_material( path, keys )
            elif "blendable" in shader:
                mat = standard_material( path, keys, "A" )
            elif "water" in shader:
                mat = water_material( path, keys )
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
        # Source2Viewer writes s&box ( x, y, z ) inches as glTF ( y, z, x ) metres (its TRANSFORMSOURCETOGLTF: pitch
        # and roll -90 degrees, then 0.0254), baked into the vertices.
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


# The materials of each cloud model's LOD 0 primitives, in the glb's order (Source2Viewer couldn't load them into the
# glb). The oaks' first primitive is the trunk and boughs, the second the leaf cards.
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
# Lights, sky and camera

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


def add_sky( material_path, tint ):
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
    bpy.context.scene.world = world


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
    import OpenImageIO as oiio
    buf = oiio.ImageBuf( str( path ) )
    names = list( buf.spec().channelnames )
    pixels = buf.get_pixels( oiio.FLOAT )

    def channels( *wanted ):
        idx = []
        for w in wanted:
            hits = [ i for i, n in enumerate( names ) if n.endswith( w ) ]
            if not hits:
                raise KeyError( f"{w} not in {names}" )
            idx.append( hits[0] )
        return pixels[..., idx]

    return channels


def finish_view( exr, png, cam_pos, fog, look, exposure ):
    """ Fog, exposure, ACES, the colour temperature and the vignette, as the scene's Look volume shows the render. """
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
    out = aces( np.maximum( rgb, 0 ) * exposure )
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
    ap = argparse.ArgumentParser( prog="belltower_render.py" )
    ap.add_argument( "--views", default="square,west_road" )
    ap.add_argument( "--view", action="append", default=[], help="name,e,n,z,te,tn,tz,fov" )
    ap.add_argument( "--size", default="1280x720" )
    ap.add_argument( "--samples", type=int, default=64 )
    ap.add_argument( "--bounces", type=int, default=2 )
    ap.add_argument( "--out", default=str( TEMP / "renders" ) )
    ap.add_argument( "--cpu", action="store_true" )
    ap.add_argument( "--threads", type=int, default=0, help="CPU threads (0: all)" )
    ap.add_argument( "--no-trees", action="store_true" )
    ap.add_argument( "--no-vista", action="store_true" )
    ap.add_argument( "--texture-limit", default="2048" )
    ap.add_argument( "--exposure", type=float, default=None )
    return ap.parse_args( argv )


def main():
    args = parse_args()
    started = time.time()
    views = { v[0]: v for v in literal( ROOT / "Tools/belltower_map.py", "VIEWS" ) }
    wanted = [ views[name] for name in args.views.split( "," ) if name ] if args.views != "all" else list( views.values() )
    for custom in args.view:
        parts = custom.split( "," )
        nums = [ float( x ) for x in parts[1:] ]
        wanted.append( ( parts[0], tuple( nums[0:3] ), tuple( nums[3:6] ), nums[6] if len( nums ) > 6 else 80 ) )
    exposure = args.exposure or literal( ROOT / "Tools/belltower_sky.py", "DESIGN_EXPOSURE" )

    bpy.ops.wm.read_factory_settings( use_empty=True )
    scene = bpy.context.scene
    found = read_scene()

    placed = {}
    for path, world, tint in found["models"]:
        if args.no_vista and "vista" in path:
            continue
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
    if found["sky"]:
        add_sky( found["sky"][0], found["sky"][1] )
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

    out = Path( args.out )
    out.mkdir( parents=True, exist_ok=True )
    for name, eye, target, fov in wanted:
        cam = set_camera( eye, target, fov )
        exr = out / f"{name}.exr"
        scene.render.filepath = str( exr )
        t0 = time.time()
        bpy.ops.render.render( write_still=True )
        finish_view( exr, out / f"{name}.png", tuple( cam.location ), found["fog"], found["look"], exposure )
        print( f"{name}: {time.time() - t0:.0f} s -> {out / ( name + '.png' )}" )


if __name__ == "__main__":
    main()
