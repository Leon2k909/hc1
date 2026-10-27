"""Blender-only comparison of exported structural assets; never accesses S&box.

Run Blender --background --factory-startup --threads 4 --python this_file.py.
Lighting and shader approximations are for geometry inspection, not engine QA.
"""
import bpy
import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/forestbase'
ASSETS=ROOT/'Assets'
parser=argparse.ArgumentParser()
parser.add_argument('--state',choices=('before','rail-before','after','sheds-before','sheds-after','facade-before','facade-after'),default='after')
parser.add_argument('--view',choices=('barracks-frame','bridge-junction','motor-roof','motor-interior','workshop-roof','workshop-interior'),default='bridge-junction')
parser.add_argument('--samples',type=int,default=48)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
CHUNKS=(('motor',) if args.view.startswith('motor-') else ('workshop',) if args.view.startswith('workshop-')
        else ('barracks','command','links') if args.view=='barracks-frame' else ('command','links'))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)


def material(path):
    name=str(path.relative_to(ASSETS))
    if name in bpy.data.materials:return bpy.data.materials[name]
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear()
    bsdf=nodes.new('ShaderNodeBsdfPrincipled');output=nodes.new('ShaderNodeOutputMaterial')
    links.new(bsdf.outputs['BSDF'],output.inputs['Surface'])
    text=path.read_text()
    def scalar(key,default):
        match=re.search(r'\b'+key+r'\s+"([\d.]+)"',text)
        return float(match[1]) if match else default
    bsdf.inputs['Metallic'].default_value=scalar('g_flCoatingMetalness',scalar('g_flMetalness',0))
    bsdf.inputs['Roughness'].default_value=.65
    def texture(channel):
        match=re.search(r'\bTexture'+channel+r'\s+"([^"\[ ]+)"',text)
        if not match:return None
        file=ASSETS/match[1]
        if not file.exists():return None
        node=nodes.new('ShaderNodeTexImage')
        node.image=bpy.data.images.load(str(file),check_existing=True)
        if channel!='Color':node.image.colorspace_settings.name='Non-Color'
        return node
    color=texture('Color')
    if color:
        socket=color.outputs['Color'];desat=scalar('CoatingDesaturation',0)
        if desat:
            gray=nodes.new('ShaderNodeRGBToBW');links.new(socket,gray.inputs[0])
            mix=nodes.new('ShaderNodeMixRGB');mix.inputs[0].default_value=desat
            links.new(socket,mix.inputs[1]);links.new(gray.outputs[0],mix.inputs[2]);socket=mix.outputs[0]
        tint=re.search(r'\bCoatingTint\s+"\[([^]]+)\]"',text)
        if tint:
            multiply=nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY'
            multiply.inputs[0].default_value=1
            multiply.inputs[2].default_value=(*map(float,tint[1].split()),1)
            links.new(socket,multiply.inputs[1]);socket=multiply.outputs[0]
        links.new(socket,bsdf.inputs['Base Color'])
    normal=texture('Normal')
    if normal:
        bump=nodes.new('ShaderNodeNormalMap');links.new(normal.outputs['Color'],bump.inputs['Color'])
        links.new(bump.outputs[0],bsdf.inputs['Normal'])
    rough=texture('Roughness')
    if rough:links.new(rough.outputs['Color'],bsdf.inputs['Roughness'])
    metal=texture('Metalness')
    if metal:links.new(metal.outputs['Color'],bsdf.inputs['Metallic'])
    if 'forestbase_lamp.shader' in text:
        bsdf.inputs['Emission Color'].default_value=(1,.61,.32,1)
        bsdf.inputs['Emission Strength'].default_value=3
    return mat


def import_set(folder,label):
    objects=[]
    for chunk in CHUNKS:
        source=folder if (folder/(chunk+'.obj')).exists() else ASSETS/'models/maps/forestbase'
        bpy.ops.wm.obj_import(filepath=str(source/(chunk+'.obj')),forward_axis='Z',up_axis='Y')
        obj=bpy.context.selected_objects[0]
        obj.name=label+' '+chunk;obj.scale=(.0254,)*3;obj.rotation_euler.z=math.pi/2
        remaps=dict(re.findall(r'from = "([^"]+)\.vmat" to = "([^"]+)"',(source/(chunk+'.vmdl')).read_text()))
        for slot in obj.material_slots:
            if slot.material:
                name=re.sub(r'\.\d{3}$','',slot.material.name)
                if name in remaps:slot.material=material(ASSETS/remaps[name])
        objects.append(obj)
    return objects


folder={'before':OUT/'structures-before','rail-before':OUT/'rail-truss-before',
        'facade-before':OUT/'facade-piers-before/Assets/models/maps/forestbase',
        'facade-after':OUT/'facade-piers-stage/models/maps/forestbase',
        'sheds-before':OUT/'sheds-before/Assets/models/maps/forestbase','sheds-after':OUT/'sheds-stage',
        'after':ASSETS/'models/maps/forestbase'}[args.state]
objects=import_set(folder,args.state)


def plan(e,n,z):return Vector((n,-e,z))*.0254


bpy.ops.mesh.primitive_plane_add(size=180)
ground=bpy.context.object
ground.data.materials.append(material(ASSETS/'materials/forestbase/scans/asphalt_02.vmat'))
world=bpy.context.scene.world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.25,.30,.39,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.55
light_data=bpy.data.lights.new('Independent inspection daylight','SUN');light_data.energy=1.5
light=bpy.data.objects.new(light_data.name,light_data);bpy.context.collection.objects.link(light)
light.rotation_euler=(math.radians(28),math.radians(-35),math.radians(-25))
light_data.color=(.80,.88,1)
for e,n,z in [(-1120,620,215),(-810,620,360),(100,690,215),(405,690,360)]:
    data=bpy.data.lights.new('Independent warm inspection light','AREA')
    data.energy=100;data.color=(1,.68,.38);data.size=1.4
    obj=bpy.data.objects.new(data.name,data);bpy.context.collection.objects.link(obj)
    obj.location=plan(e,n-10,z);obj.rotation_euler=(plan(e,n+60,z-70)-obj.location).to_track_quat('-Z','Y').to_euler()
if args.view.startswith(('motor-','workshop-')):
    e,n,w=(-1060,-555,720) if args.view.startswith('motor-') else (1100,520,660)
    for x in (e-w*.25,e+w*.25):
        data=bpy.data.lights.new('Independent warm hall inspection light','AREA')
        data.energy=200;data.color=(1,.68,.38);data.size=1.2
        obj=bpy.data.objects.new(data.name,data);bpy.context.collection.objects.link(obj)
        obj.location=plan(x,n,145);obj.rotation_euler=(plan(x,n,0)-obj.location).to_track_quat('-Z','Y').to_euler()
camera_data=bpy.data.cameras.new('Inspection camera');camera=bpy.data.objects.new(camera_data.name,camera_data)
bpy.context.collection.objects.link(camera);bpy.context.scene.camera=camera;camera_data.lens=35
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
scene.cycles.samples=max(1,args.samples);scene.cycles.use_denoising=False
scene.render.use_simplify=True;scene.cycles.texture_limit_render='1024'
scene.render.resolution_x=1024;scene.render.resolution_y=682;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
views=[('barracks-frame',(-1510,-150,500),(-950,760,205)),
       ('bridge-junction',(720,620,325),(1050,940,229)),
       ('motor-roof',(-1750,-1280,620),(-1060,-555,125)),
       ('motor-interior',(-1070,-1110,90),(-1060,-455,125)),
       ('workshop-roof',(1730,-210,650),(1100,520,125)),
       ('workshop-interior',(1100,30,85),(1100,600,130))]
files=[]
for name,eye,target in views:
    if name!=args.view:continue
    camera.location=plan(*eye);camera.rotation_euler=(plan(*target)-camera.location).to_track_quat('-Z','Y').to_euler()
    file=f'{name}-{args.state}.png';scene.render.filepath=str(OUT/file)
    bpy.ops.render.render(write_still=True);files.append(file)
(OUT/f'structures-{args.view}-{args.state}.json').write_text(json.dumps({'renderer':'Blender Cycles CPU',
    'scope':'Actual exported before/after meshes and surface maps; independent approximate lighting. No S&box access or engine appearance claim.',
    'textureLimit':1024,'denoising':False,'samples':scene.cycles.samples,
    'sourceMeshes':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
        for chunk in CHUNKS
        for path in [(folder if (folder/(chunk+'.obj')).exists() else ASSETS/'models/maps/forestbase')/(chunk+'.obj')]},
    'views':files},indent=2)+'\n')
