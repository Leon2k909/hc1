"""
Renders build_sheet.py's prop sheet in headless Blender (Cycles), lit by Riverdale's low morning sun.

    blender -b --factory-startup --python output/riverdale/aaa/props/render_sheet.py -- <sheet dir> [camera ...]

Plan ( e, n, z ) inches is Blender ( -e, -n, z ) after the OBJ import (map_kit writes world ( n, -e, z ) as Y-up).
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index( "--" ) + 1:]
SHEET = Path( args[0] )
ONLY = set( args[1:] )


def srgb_to_linear( c ):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ( ( c + 0.055 ) / 1.055 ) ** 2.4


def plan( p ):
    return Vector( ( -p[0], -p[1], p[2] ) )


bpy.ops.wm.read_factory_settings( use_empty=True )
bpy.ops.wm.obj_import( filepath=str( SHEET / "props_sheet.obj" ) )
mats = json.loads( ( SHEET / "materials.json" ).read_text() )

for mat in bpy.data.materials:
    spec = mats.get( mat.name )
    if spec is None:
        continue
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get( "Principled BSDF" )
    for link in list( nt.links ):
        if link.to_node == bsdf:
            nt.links.remove( link )
    bsdf.inputs["Metallic"].default_value = float( spec.get( "metal", 0.0 ) )
    bsdf.inputs["Roughness"].default_value = float( spec.get( "rough", 0.6 ) )
    if spec.get( "texture" ):
        tex = nt.nodes.new( "ShaderNodeTexImage" )
        tex.image = bpy.data.images.load( spec["texture"] )
        if spec.get( "color" ) and mat.name.startswith( "rv_letters" ) is False and spec.get( "glow", 0 ) == 0 and "PAINT" in "":
            pass
        nt.links.new( tex.outputs["Color"], bsdf.inputs["Base Color"] )
        if spec.get( "roughmap" ):
            rt = nt.nodes.new( "ShaderNodeTexImage" )
            rt.image = bpy.data.images.load( spec["roughmap"] )
            rt.image.colorspace_settings.name = "Non-Color"
            nt.links.new( rt.outputs["Color"], bsdf.inputs["Roughness"] )
        if spec.get( "normal" ):
            nm = nt.nodes.new( "ShaderNodeTexImage" )
            nm.image = bpy.data.images.load( spec["normal"] )
            nm.image.colorspace_settings.name = "Non-Color"
            nmap = nt.nodes.new( "ShaderNodeNormalMap" )
            nmap.inputs["Strength"].default_value = 0.8
            nt.links.new( nm.outputs["Color"], nmap.inputs["Color"] )
            nt.links.new( nmap.outputs["Normal"], bsdf.inputs["Normal"] )
    elif spec.get( "color" ):
        r, g, b = ( srgb_to_linear( c ) for c in spec["color"] )
        bsdf.inputs["Base Color"].default_value = ( r, g, b, 1.0 )
    if spec.get( "color" ) and mat.name.startswith( "rv_letters" ):
        r, g, b = ( srgb_to_linear( c ) for c in spec["color"] )
        bsdf.inputs["Base Color"].default_value = ( r, g, b, 1.0 )
    if spec.get( "alpha" ):
        at = nt.nodes.new( "ShaderNodeTexImage" )
        at.image = bpy.data.images.load( spec["alpha"] )
        at.image.colorspace_settings.name = "Non-Color"
        nt.links.new( at.outputs["Color"], bsdf.inputs["Alpha"] )
    if spec.get( "glow", 0 ) > 0:
        r, g, b = ( srgb_to_linear( c ) for c in spec["color"] )
        bsdf.inputs["Emission Color"].default_value = ( r, g, b, 1.0 )
        bsdf.inputs["Emission Strength"].default_value = float( spec["glow"] ) * 0.6
    if spec.get( "glass" ):
        bsdf.inputs["Transmission Weight"].default_value = 1.0
        bsdf.inputs["Roughness"].default_value = 0.05

for ob in bpy.context.scene.objects:
    if ob.type == "MESH":
        for poly in ob.data.polygons:
            poly.use_smooth = True

scene = bpy.context.scene
scene.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
for kind in ( "OPTIX", "CUDA" ):
    try:
        prefs.compute_device_type = kind
        prefs.get_devices()
        if any( d.type == kind for d in prefs.devices ):
            for d in prefs.devices:
                d.use = d.type == kind
            scene.cycles.device = "GPU"
            break
    except Exception:
        continue
scene.cycles.samples = 96
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = -1.3

world = bpy.data.worlds.new( "sky" )
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
sky = world.node_tree.nodes.new( "ShaderNodeTexSky" )
try:
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians( 16 )
    sky.sun_rotation = math.radians( 180 + 33 )
    sky.sun_disc = False
except Exception:
    pass
world.node_tree.links.new( sky.outputs["Color"], bg.inputs["Color"] )
bg.inputs["Strength"].default_value = 0.35

sun = bpy.data.objects.new( "Sun", bpy.data.lights.new( "Sun", "SUN" ) )
scene.collection.objects.link( sun )
sun.data.energy = 4.0
sun.data.color = ( 1.0, 0.82, 0.62 )
sun.data.angle = math.radians( 1.5 )
# Riverdale's sun: 16 degrees up, from 33 degrees north of east (plan ( cos, sin ) of yaw 33 from east), as Blender
# ( -e, -n ).
d = Vector( ( -math.cos( math.radians( 33 ) ), -math.sin( math.radians( 33 ) ), 0 ) ) * math.cos( math.radians( 16 ) ) + Vector( ( 0, 0, math.sin( math.radians( 16 ) ) ) )
sun.rotation_euler = ( -d ).to_track_quat( "-Z", "Y" ).to_euler()
fill = bpy.data.objects.new( "Fill", bpy.data.lights.new( "Fill", "SUN" ) )
scene.collection.objects.link( fill )
fill.data.energy = 0.6
fill.data.color = ( 0.7, 0.8, 1.0 )
fill.rotation_euler = ( math.radians( 50 ), 0, math.radians( 200 ) )
for light in json.loads( ( SHEET / "lights.json" ).read_text() ):
    pl = bpy.data.objects.new( light["name"], bpy.data.lights.new( light["name"], "POINT" ) )
    scene.collection.objects.link( pl )
    pl.location = plan( light["at"] )
    rgb = [ float( x ) for x in light["colour"].split( "," )[:3] ]
    pl.data.color = rgb
    pl.data.energy = 2.0e5

cam = bpy.data.objects.new( "Camera", bpy.data.cameras.new( "Camera" ) )
scene.collection.objects.link( cam )
scene.camera = cam
cam.data.clip_start = 1.0
cam.data.clip_end = 100000.0
for c in json.loads( ( SHEET / "cameras.json" ).read_text() ):
    if ONLY and c["name"] not in ONLY:
        continue
    eye, target = plan( c["eye"] ), plan( c["target"] )
    cam.location = eye
    cam.rotation_euler = ( target - eye ).to_track_quat( "-Z", "Y" ).to_euler()
    cam.data.angle = math.radians( c["fov"] )
    scene.render.filepath = str( SHEET / f"render_{c['name']}.png" )
    bpy.ops.render.render( write_still=True )
    print( "rendered", c["name"] )
