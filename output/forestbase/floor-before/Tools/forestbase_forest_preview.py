"""Blender CPU comparison of saved/staged west forest, using real source assets.

Static lighting/material approximations; branch models use their declared LOD1.
This is not an engine capture, native LOD validation or performance benchmark.
"""
import argparse
import bpy
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector

ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'Assets';OUT=ROOT/'output/forestbase'
STAGE=OUT/'forest-stage'
parser=argparse.ArgumentParser();parser.add_argument('--state',choices=('before','after'),default='after')
parser.add_argument('--view',choices=('ground','raised'),default='ground')
parser.add_argument('--lod',choices=('lod0','lod1','lod2'),default='lod1')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
CACHE={};loaded=[]


def material(name,path):
    key='forest-inspection '+str(path)
    if key in bpy.data.materials:return bpy.data.materials[key]
    mat=bpy.data.materials.new(key);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear()
    output=nodes.new('ShaderNodeOutputMaterial');bsdf=nodes.new('ShaderNodeBsdfPrincipled')
    links.new(bsdf.outputs[0],output.inputs['Surface']);bsdf.inputs['Roughness'].default_value=.8
    if name.startswith(('waterfall_','plunge_basin')):
        bsdf.inputs['Alpha'].default_value=0
        return mat
    if not path or not path.exists():
        bsdf.inputs['Base Color'].default_value=(.11,.12,.10,1)
        return mat
    text=path.read_text()
    color=None
    for channel,socket in (('Color','Base Color'),('Normal','Normal'),('Roughness','Roughness'),('Translucency','Alpha')):
        match=re.search(r'\bTexture'+channel+r'\s+"([^"\[ ]+)"',text)
        if not match or not (ASSETS/match[1]).exists():continue
        image=nodes.new('ShaderNodeTexImage');image.image=bpy.data.images.load(str(ASSETS/match[1]),check_existing=True)
        if channel!='Color':image.image.colorspace_settings.name='Non-Color'
        value=image.outputs['Color']
        if channel=='Normal':
            normal=nodes.new('ShaderNodeNormalMap');links.new(value,normal.inputs['Color']);value=normal.outputs[0]
        elif channel=='Translucency':
            threshold=nodes.new('ShaderNodeMath');threshold.operation='GREATER_THAN'
            match=re.search(r'g_flAlphaTestReference\s+"([\d.]+)"',text)
            threshold.inputs[1].default_value=float(match[1]) if match else .25
            links.new(value,threshold.inputs[0]);value=threshold.outputs[0]
        elif channel=='Color':color=value;continue
        links.new(value,bsdf.inputs[socket])
    if color:
        info=nodes.new('ShaderNodeObjectInfo');tint=nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY'
        tint.inputs[0].default_value=1;links.new(color,tint.inputs[1]);links.new(info.outputs['Color'],tint.inputs[2])
        links.new(tint.outputs[0],bsdf.inputs['Base Color'])
    return mat


def mesh(model):
    source=STAGE/model if args.state=='after' and (STAGE/model).exists() else ASSETS/model
    text=source.read_text()
    filenames=re.findall(r'name = "([^"]+)"\s+filename = "([^"]+\.obj)"',text)
    assert filenames,model
    filename=next((file for lod,file in filenames if lod==args.lod),filenames[0][1])
    if filename in CACHE:return CACHE[filename]
    mesh_source=STAGE/filename if args.state=='after' and (STAGE/filename).exists() else ASSETS/filename
    bpy.ops.wm.obj_import(filepath=str(mesh_source),forward_axis='Z',up_axis='Y')
    obj=bpy.context.selected_objects[0];obj.rotation_euler.z=math.pi/2
    basis=obj.rotation_euler.to_matrix().to_4x4()
    remaps=dict(re.findall(r'from = "([^"]+)\.vmat" to = "([^"]+)"',text))
    default=re.search(r'global_default_material = "([^"]+)"',text)
    if default and re.search(r'use_global_default\s*=\s*true',text):
        obj.data.materials.clear();obj.data.materials.append(material('scanned_rock',ASSETS/default[1]))
        for polygon in obj.data.polygons:polygon.material_index=0
    else:
        for slot in obj.material_slots:
            if slot.material:
                name=re.sub(r'\.\d{3}$','',slot.material.name)
                path=ASSETS/remaps[name] if name in remaps else None
                slot.material=material(name,path)
    data=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
    CACHE[filename]=(data,basis);loaded.append(filename)
    return data,basis


scene_path=STAGE/'forestbase.scene' if args.state=='after' else OUT/'forest-before/Assets/scenes/maps/ForestBase/forestbase.scene'
scene_bytes=scene_path.read_bytes();document=json.loads(scene_bytes);instances=[]
def visit(nodes):
    for node in nodes:
        renderer=next((c for c in node.get('Components',[]) if c['__type']=='Sandbox.ModelRenderer'),None)
        if renderer:
            position=tuple(map(float,node['Position'].split(',')));e=-position[1]
            model=renderer['Model'];name=node['Name']
            tree='/forestbase/fir/' in model or '/forestbase/sapling/' in model
            scenery=name.startswith(('Rock ','Cascade cliff ','Distant mountain ','Shore '))
            if name in ('Ground','Vista') or e<-1450 and (tree or scenery):
                data,basis=mesh(model);obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
                qx,qy,qz,qw=map(float,node['Rotation'].split(','));rotation=Quaternion((qw,qx,qy,qz)).to_matrix().to_4x4()
                scale=tuple(float(v)*.0254 for v in node['Scale'].split(','))
                obj.matrix_world=Matrix.Translation(Vector(position)*.0254)@rotation@Matrix.Diagonal((*scale,1))@basis
                obj.color=tuple(map(float,renderer.get('Tint','1,1,1,1').split(',')))
                instances.append(name)
        visit(node.get('Children',[]))
visit(document['GameObjects'])

world=bpy.context.scene.world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.24,.29,.36,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.7
sun=bpy.data.lights.new('Independent forest inspection daylight','SUN');sun.energy=1.7;sun.angle=math.radians(5)
light=bpy.data.objects.new(sun.name,sun);bpy.context.collection.objects.link(light)
light.rotation_euler=(math.radians(28),math.radians(-20),math.radians(-35))
def plan(e,n,z):return Vector((n,-e,z))*.0254
eye=(-1300,-800,180) if args.view=='ground' else (-850,-1550,1350)
target=(-3100,350,450) if args.view=='ground' else (-3350,600,400)
camera_data=bpy.data.cameras.new('Forest inspection');camera=bpy.data.objects.new(camera_data.name,camera_data)
bpy.context.collection.objects.link(camera);camera_data.lens=32;bpy.context.scene.camera=camera
camera.location=plan(*eye);camera.rotation_euler=(plan(*target)-camera.location).to_track_quat('-Z','Y').to_euler()
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
scene.cycles.use_denoising=False;scene.cycles.transparent_max_bounces=32
scene.render.use_simplify=True;scene.cycles.texture_limit_render='1024'
scene.render.resolution_x=1024;scene.render.resolution_y=768;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
suffix='' if args.lod=='lod1' else '-'+args.lod
file=f'forest-{args.view}{suffix}-{args.state}.png';scene.render.filepath=str(OUT/file)
bpy.ops.render.render(write_still=True)
(OUT/f'forest-{args.view}{suffix}-{args.state}.json').write_text(json.dumps(dict(
    scope=f'Real saved/staged west forest, {args.lod} meshes, static approximate lighting/materials; no native LOD/shadow/performance acceptance. Water hidden.',
    renderer='Blender Cycles CPU',samples=24,view=file,sceneSha256=hashlib.sha256(scene_bytes).hexdigest(),
    instances=instances,meshSources=loaded),indent=2)+'\n')
