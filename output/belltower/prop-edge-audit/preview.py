"""Render exact staged geometry/PBR maps in extracted town-window context.

Blender construction QA only. Engine shader translation is approximate and these
images must never be described as native s&box screenshots.
"""
from pathlib import Path
from array import array
import argparse
import json
import math
import os
import re
import sys
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--stage',default='stage-v10')
parser.add_argument('--out',default='revision-v2')
parser.add_argument('--view',choices=('front','detail'),default='front')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
STAGE=ROOT/'output/belltower/shop-displays'/args.stage
OUT=ROOT/'output/belltower/shop-displays'/args.out;OUT.mkdir(parents=True,exist_ok=True)
manifest=json.loads((STAGE/'manifest.json').read_text())
record=manifest['west_apertures'][1]
origin=Vector(record['origin']);out=Vector(record['outward']);right=out.cross(Vector((0,0,1)));inside=-out
UNIT=.0254
engine=Path(os.environ['FACEPUNCH_ENGINE'])
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)


def resource(path):
    for base in (STAGE/'Assets',ROOT/'Assets',engine/'core'):
        p=base/path
        if p.exists():return p
    raise FileNotFoundError(path)


def remaps(path):
    return {a.removesuffix('.vmat'):b for a,b in re.findall(r'from\s*=\s*"([^"]+)"\s+to\s*=\s*"([^"]+)"',path.read_text())}


def parse_material(path):
    return dict(re.findall(r'^\s*(\w+)\s+"([^"]*)"',path.read_text(),re.M))


def floats(value):return [float(x) for x in value.strip('[] ').split()]


material_cache={}
def material(paint,paths):
    path=paths.get(paint,'materials/buildings/'+paint+'.vmat')
    if paint.startswith('shopfront_'):path='materials/belltower/'+paint+'.vmat'
    if path in material_cache:return material_cache[path]
    p=parse_material(resource(path));m=bpy.data.materials.new(paint);m.use_nodes=True
    nodes=m.node_tree.nodes;links=m.node_tree.links;bsdf=nodes.get('Principled BSDF')
    glass=p.get('shader')=='shaders/glass.shader'
    tint=floats(p.get('g_vShopTint',p.get('g_flTintColor',p.get('g_vColorTint','[1 1 1]'))))[:3]
    bsdf.inputs['Base Color'].default_value=(*tint,1)
    bsdf.inputs['Metallic'].default_value=float(p.get('g_flShopMetalness',p.get('g_flMetalness','0')))
    rough_scale=1.0 if glass else float(p.get('g_flShopRoughness',p.get('g_flRoughnessScaleFactor','1')))
    bsdf.inputs['Roughness'].default_value=min(1,rough_scale*.65)
    uv=nodes.new('ShaderNodeTexCoord').outputs['UV']
    if 'g_vPlasterUvScale' in p:
        scale=nodes.new('ShaderNodeVectorMath');scale.operation='MULTIPLY'
        s=floats(p['g_vPlasterUvScale']);scale.inputs[1].default_value=(s[0],s[1],1)
        links.new(uv,scale.inputs[0]);uv=scale.outputs[0]
    def texture(key,noncolor=False):
        if key not in p:return None
        img=bpy.data.images.load(str(resource(p[key])),check_existing=True)
        if noncolor:img.colorspace_settings.name='Non-Color'
        node=nodes.new('ShaderNodeTexImage');node.image=img
        links.new(uv,node.inputs['Vector']);return node.outputs['Color']
    colour=texture('TextureColor')
    if colour:
        multiply=nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1
        multiply.inputs[2].default_value=(*tint,1);links.new(colour,multiply.inputs[1])
        links.new(multiply.outputs[0],bsdf.inputs['Base Color'])
    rough=texture('TextureRoughness',True)
    if rough:
        scale=nodes.new('ShaderNodeMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=rough_scale
        links.new(rough,scale.inputs[0]);links.new(scale.outputs[0],bsdf.inputs['Roughness'])
    normal=texture('TextureNormal',True)
    if normal:
        node=nodes.new('ShaderNodeNormalMap');node.inputs['Strength'].default_value=.38 if glass else .65
        links.new(normal,node.inputs['Color']);links.new(node.outputs[0],bsdf.inputs['Normal'])
    if glass:
        bottle=paint in ('shop2_green','shop2_amber')
        bsdf.inputs['Transmission Weight'].default_value=.86 if bottle else 1
        bsdf.inputs['IOR'].default_value=1.46 if bottle else 1.001
        # Optical transport is a Cycles approximation of the engine's layered
        # screen-space glass, not a claim of matching the native shader.
    material_cache[path]=m
    return m


def read_obj(path,context=False):
    positions=array('f',(0,0,0));coords=array('f',(0,0));normals=array('f',(0,0,1))
    points=[];uvs=[];ns=[];faces=[];paints=[];paint=None
    def pos(i):return Vector(positions[i*3:i*3+3])
    def norm(i):return Vector(normals[i*3:i*3+3])
    def uv(i):return (coords[i*2],1-coords[i*2+1])
    bounds=((-record['width']/2-20,record['width']/2+20),(-20,4),(-12,118))
    def clip(poly):
        for axis,(lo,hi) in enumerate(bounds):
            for edge,sign in ((lo,1),(hi,-1)):
                src=poly;poly=[]
                if not src:return []
                for a,b in zip(src,src[1:]+src[:1]):
                    ia=(a[0][axis]-edge)*sign>=-1e-6;ib=(b[0][axis]-edge)*sign>=-1e-6
                    if ia:poly.append(a)
                    if ia!=ib:
                        t=(edge-a[0][axis])/(b[0][axis]-a[0][axis])
                        poly.append((a[0].lerp(b[0],t),
                            tuple(x+(y-x)*t for x,y in zip(a[1],b[1])),a[2].lerp(b[2],t)))
        return poly
    for line in path.open():
        if line.startswith('v '):
            x,y,z=map(float,line.split()[1:]);p=Vector((-x,z,y))-origin
            positions.extend((p.dot(right),p.dot(inside),p.z))
        elif line.startswith('vt '):coords.extend(map(float,line.split()[1:3]))
        elif line.startswith('vn '):
            x,y,z=map(float,line.split()[1:]);p=Vector((-x,z,y));normals.extend((p.dot(right),p.dot(inside),p.z))
        elif line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):
            if context and not (paint.startswith(('trim_','plaster_','shopfront_'))):continue
            fields=[list(map(int,f.split('/'))) for f in line.split()[1:]]
            tri=[pos(f[0]) for f in fields]
            if context:
                if any(max(p[i] for p in tri)<lo or min(p[i] for p in tri)>hi for i,(lo,hi) in enumerate(bounds)):continue
            elif not all(abs(p.x)<record['width']/2+2 and -.1<p.y<38 and -.1<p.z<105 for p in tri):continue
            poly=[(p,uv(f[1]),norm(f[2])) for p,f in zip(tri,fields)]
            if context:poly=clip(poly)
            if len(poly)<3:continue
            for i in range(1,len(poly)-1):
                ts=[poly[0],poly[i],poly[i+1]]
                if (ts[1][0]-ts[0][0]).cross(ts[2][0]-ts[0][0]).length<1e-8:continue
                if (ts[1][0]-ts[0][0]).cross(ts[2][0]-ts[0][0]).dot(sum((v[2] for v in ts),Vector()))<0:ts[1],ts[2]=ts[2],ts[1]
                start=len(points);points.extend(tuple(p*UNIT) for p,_,_ in ts)
                uvs.extend(v[1] for v in ts);ns.extend(tuple(v[2].normalized()) for v in ts)
                faces.append(tuple(range(start,start+3)));paints.append(paint)
    mesh=bpy.data.meshes.new(path.stem+(' context' if context else ' display'))
    mesh.from_pydata(points,[],faces);mesh.update()
    obj=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(obj)
    paths=remaps(path.with_suffix('.vmdl'));keys=sorted(set(paints))
    for key in keys:obj.data.materials.append(material(key,paths))
    uv_layer=mesh.uv_layers.new(name='UVMap')
    for i,poly in enumerate(mesh.polygons):
        poly.material_index=keys.index(paints[i]);poly.use_smooth=True
        for loop in poly.loop_indices:uv_layer.data[loop].uv=uvs[loop]
    mesh.normals_split_custom_set(ns)
    return len(faces)


count=read_obj(STAGE/'Assets'/manifest['model_path'].replace('.vmdl','.obj'))
context_count=read_obj(ROOT/'Assets/models/maps/belltower/belltower_west.obj',True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.cycles.max_bounces=8;scene.cycles.transmission_bounces=6
scene.world.use_nodes=True;nodes=scene.world.node_tree.nodes;links=scene.world.node_tree.links
worlds=Path(bpy.app.binary_path).parent/'5.1/datafiles/studiolights/world'
hdri=worlds/'forest.exr'
if hdri.exists():
    env=nodes.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load(str(hdri))
    links.new(env.outputs['Color'],nodes['Background'].inputs['Color'])
else:nodes['Background'].inputs['Color'].default_value=(.65,.72,.82,1)
nodes['Background'].inputs['Strength'].default_value=.32
for loc,power,size in [((-75,-120,158),580,95),((90,-70,75),100,60)]:
    bpy.ops.object.light_add(type='AREA',location=tuple(v*UNIT for v in loc))
    light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size*UNIT
    light.rotation_euler=(Vector((0,19*UNIT,58*UNIT))-light.location).to_track_quat('-Z','Y').to_euler()
if args.view=='front':loc,target,lens=(27,-180,68),(0,17,55),45
else:loc,target,lens=(21,-35,61),(-8,23,57),50
bpy.ops.object.camera_add(location=tuple(v*UNIT for v in loc));camera=bpy.context.object
camera.rotation_euler=(Vector(tuple(v*UNIT for v in target))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.lens=lens;camera.data.clip_end=100
scene.camera=camera;scene.render.resolution_x=1400;scene.render.resolution_y=1150;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/(args.view+'.png'))
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.35
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('construction-'+args.view+'.blend')))
bpy.ops.render.render(write_still=True)
result={'construction_preview':scene.render.filepath,'staged_display_triangles':count,'extracted_context_triangles':context_count,
    'native_engine_capture':False,'stage':args.stage,'view':args.view,'physical_goods_and_labels':True}
(OUT/(args.view+'.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
