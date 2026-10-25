"""Offline inspection of exported cascade/scan geometry with approximate shaders.

Blender --background --factory-startup --threads 4 --python this_file.py --
    --state before|after --view front|side
Native water animation, fog, foliage and spray are deliberately not evaluated.
"""
import argparse
import ast
import bpy
import json
import math
import re
import sys
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'Assets';OUT=ROOT/'output/forestbase'
parser=argparse.ArgumentParser()
parser.add_argument('--state',choices=('before','after'),default='after')
parser.add_argument('--view',choices=('front','side'),default='front')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)


def image_texture(nodes,channel,file):
    node=nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(file),check_existing=True)
    if channel!='Color':node.image.colorspace_settings.name='Non-Color'
    return node


def material(name,path):
    cache='cascade-inspection '+name
    if cache in bpy.data.materials:return bpy.data.materials[cache]
    mat=bpy.data.materials.new(cache);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear()
    bsdf=nodes.new('ShaderNodeBsdfPrincipled');output=nodes.new('ShaderNodeOutputMaterial')
    links.new(bsdf.outputs[0],output.inputs['Surface']);bsdf.inputs['Roughness'].default_value=.65
    if name in ('waterfall_spray','waterfall_impact','waterfall_plunge'):
        bsdf.inputs['Alpha'].default_value=0
        return mat
    if name.startswith('waterfall_'):
        # Same static approximation in both states: this isolates geometry.
        # Native flow, emission and animated fraying require engine review.
        tex=image_texture(nodes,'Mask',ASSETS/'materials/forestbase/waterfall_froth_v2.png')
        uv=nodes.new('ShaderNodeTexCoord');scale=nodes.new('ShaderNodeVectorMath');scale.operation='MULTIPLY'
        scale.inputs[1].default_value=(3.4 if args.state=='after' else .85,2.6,1)
        links.new(uv.outputs['UV'],scale.inputs[0]);links.new(scale.outputs[0],tex.inputs[0])
        ramp=nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position=.12;ramp.color_ramp.elements[0].color=(.03,.07,.09,1)
        ramp.color_ramp.elements[1].position=.72;ramp.color_ramp.elements[1].color=(.65,.73,.76,1)
        links.new(tex.outputs['Color'],ramp.inputs[0]);links.new(ramp.outputs[0],bsdf.inputs['Base Color'])
        links.new(ramp.outputs[0],bsdf.inputs['Emission Color']);bsdf.inputs['Emission Strength'].default_value=.18
        bsdf.inputs['Roughness'].default_value=.72
        separate=nodes.new('ShaderNodeSeparateXYZ');links.new(uv.outputs['UV'],separate.inputs[0])
        inverse=nodes.new('ShaderNodeMath');inverse.operation='SUBTRACT';inverse.inputs[0].default_value=1
        links.new(separate.outputs['X'],inverse.inputs[1])
        edge=nodes.new('ShaderNodeMath');edge.operation='MINIMUM'
        links.new(separate.outputs['X'],edge.inputs[0]);links.new(inverse.outputs[0],edge.inputs[1])
        fade=nodes.new('ShaderNodeMath');fade.operation='MULTIPLY';fade.use_clamp=True;fade.inputs[1].default_value=12
        links.new(edge.outputs[0],fade.inputs[0])
        density=nodes.new('ShaderNodeMath');density.operation='MULTIPLY_ADD'
        density.inputs[1].default_value=.55;density.inputs[2].default_value=.2
        links.new(tex.outputs['Color'],density.inputs[0])
        opacity=nodes.new('ShaderNodeMath');opacity.operation='MULTIPLY'
        links.new(fade.outputs[0],opacity.inputs[0]);links.new(density.outputs[0],opacity.inputs[1])
        links.new(opacity.outputs[0],bsdf.inputs['Alpha'])
        return mat
    if name=='plunge_basin':
        bsdf.inputs['Base Color'].default_value=(.02,.055,.06,1);bsdf.inputs['Roughness'].default_value=.12
        return mat
    if not path or not path.exists():
        bsdf.inputs['Base Color'].default_value=(.08,.07,.055,1)
        return mat
    text=path.read_text()
    projection=name=='cascade_rock'
    vector=None
    if projection:
        geometry=nodes.new('ShaderNodeNewGeometry');mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='SCALE'
        mapping.inputs[3].default_value=1/(106*.0254)
        links.new(geometry.outputs['Position'],mapping.inputs[0]);vector=mapping.outputs[0]
    for channel,socket in (('Color','Base Color'),('Roughness','Roughness'),('Normal','Normal')):
        match=re.search(r'\bTexture'+channel+r'\s+"([^"\[ ]+)"',text)
        if not match or not (ASSETS/match[1]).exists():continue
        if projection and channel=='Normal':continue
        texture=image_texture(nodes,channel,ASSETS/match[1])
        if vector:
            texture.projection='BOX';texture.projection_blend=.2;links.new(vector,texture.inputs[0])
        value=texture.outputs['Color']
        if channel=='Color':
            tint=nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1
            tint.inputs[2].default_value=(.48,.53,.56,1);links.new(value,tint.inputs[1]);value=tint.outputs[0]
        if channel=='Normal':
            normal=nodes.new('ShaderNodeNormalMap');links.new(value,normal.inputs['Color']);value=normal.outputs[0]
        links.new(value,bsdf.inputs[socket])
    return mat


def plan(e,n,z):return Vector((n,-e,z))*.0254


folder=OUT/'terrace-stage' if args.state=='after' else OUT/'terrace-before/Assets/models/maps/forestbase'
bpy.ops.wm.obj_import(filepath=str(folder/'vista.obj'),forward_axis='Z',up_axis='Y')
obj=bpy.context.selected_objects[0];obj.scale=(.0254,)*3;obj.rotation_euler.z=math.pi/2
remaps=dict(re.findall(r'from = "([^"]+)\.vmat" to = "([^"]+)"',(folder/'vista.vmdl').read_text()))
for slot in obj.material_slots:
    if slot.material:
        name=re.sub(r'\.\d{3}$','',slot.material.name)
        slot.material=material(name,ASSETS/remaps[name] if name in remaps else None)

config_path=ROOT/'Tools/forestbase_cascade.py' if args.state=='after' else OUT/'terrace-before/Tools/forestbase_cascade.py'
config=ast.parse(config_path.read_text())
placements=[]
for assignment in config.body:
    if isinstance(assignment,ast.Assign) and isinstance(assignment.targets[0],ast.Name) and assignment.targets[0].id in ('SCANS','DISTANT_SCANS'):
        placements.extend(ast.literal_eval(assignment.value))
rock_material=material('scanned_cliff',ASSETS/'models/maps/forestbase/mountainside/cliff.vmat')
source=None
for e,n,z,yaw,scale in placements:
    if source is None:
        bpy.ops.wm.obj_import(filepath=str(ASSETS/'models/maps/forestbase/mountainside/cliff_lod0.obj'),forward_axis='Z',up_axis='Y')
        source=bpy.context.selected_objects[0];source.data.materials.clear();source.data.materials.append(rock_material);obj=source
    else:
        obj=source.copy();obj.data=source.data;bpy.context.collection.objects.link(obj)
    obj.location=plan(e,n,z);obj.scale=(scale*.0254,)*3;obj.rotation_euler.z=math.pi/2+math.radians(yaw)

world=bpy.context.scene.world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.20,.27,.34,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6
sun=bpy.data.lights.new('Independent inspection daylight','SUN');sun.energy=2;sun.angle=math.radians(6)
light=bpy.data.objects.new(sun.name,sun);bpy.context.collection.objects.link(light)
light.rotation_euler=(math.radians(32),math.radians(-22),math.radians(-45))
camera_data=bpy.data.cameras.new('Geometry review');camera=bpy.data.objects.new(camera_data.name,camera_data)
bpy.context.collection.objects.link(camera);bpy.context.scene.camera=camera;camera_data.lens=28
eye=(430,1350,1050) if args.view=='front' else (-900,1950,650)
target=(430,3400,380) if args.view=='front' else (430,3450,500)
camera.location=plan(*eye);camera.rotation_euler=(plan(*target)-camera.location).to_track_quat('-Z','Y').to_euler()
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=40
scene.cycles.use_denoising=False;scene.render.use_simplify=True;scene.cycles.texture_limit_render='1024'
scene.render.resolution_x=1024;scene.render.resolution_y=768;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
file=f'cascade-{args.view}-{args.state}.png';scene.render.filepath=str(OUT/file)
bpy.ops.render.render(write_still=True)
(OUT/f'cascade-{args.view}-{args.state}.json').write_text(json.dumps(dict(
    scope='Actual exported meshes and scan placements, approximate static shaders/daylight; no S&box access or native appearance claim. Spray/foliage omitted.',
    renderer='Blender Cycles CPU',samples=40,view=file),indent=2)+'\n')
