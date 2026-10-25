"""Blender construction preview of the staged mesh; this is not an engine capture."""
from pathlib import Path
import json
import math
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/belltower/shop-displays/stage-v4'
manifest=json.loads((STAGE/'manifest.json').read_text())
record=manifest['west_apertures'][1]
origin=Vector(record['origin']);out=Vector(record['outward']);up=Vector((0,0,1));right=out.cross(up);inside=-out
scale=.0254

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
verts=[None];coords=[None];normals=[None];paint=None;points=[];uvs=[];ns=[];faces=[];paints=[]
path=STAGE/'Assets/models/maps/belltower/shop-display-v1/shop_displays.obj'
for line in path.open():
    if line.startswith('v '):
        x,y,z=map(float,line.split()[1:]);p=Vector((-x,z,y))-origin
        verts.append(Vector((p.dot(right),p.dot(inside),p.z)))
    elif line.startswith('vt '):coords.append(tuple(map(float,line.split()[1:3])))
    elif line.startswith('vn '):
        x,y,z=map(float,line.split()[1:]);p=Vector((-x,z,y));normals.append(Vector((p.dot(right),p.dot(inside),p.z)))
    elif line.startswith('usemtl '):paint=line.split()[1]
    elif line.startswith('f '):
        fields=[list(map(int,f.split('/'))) for f in line.split()[1:]]
        tri=[verts[f[0]] for f in fields]
        if not all(abs(p.x)<record['width']/2+2 and -.1<p.y<38 and -.1<p.z<105 for p in tri):continue
        uv=[coords[f[1]] for f in fields];normal=[normals[f[2]] for f in fields]
        if (tri[1]-tri[0]).cross(tri[2]-tri[0]).dot(sum(normal,Vector()))<0:
            tri[1],tri[2]=tri[2],tri[1];uv[1],uv[2]=uv[2],uv[1];normal[1],normal[2]=normal[2],normal[1]
        start=len(points);points.extend(tuple(p*scale) for p in tri);uvs.extend(uv);ns.extend(tuple(n) for n in normal)
        faces.append(tuple(range(start,start+3)));paints.append(paint)

def material(name,colour,rough=.5,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*colour,1);m.use_nodes=True
    bsdf=m.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(*colour,1)
    bsdf.inputs['Roughness'].default_value=rough;bsdf.inputs['Metallic'].default_value=metal
    return m

palette={
    'furniture_wood_dark':((.16,.10,.055),.75,0),
    'furniture_wood':((.25,.17,.09),.67,0),
    'shop_bottle_green':((.055,.12,.038),.19,.05),
    'shop_bottle_amber':((.20,.085,.022),.21,.03),
    'shop_stoneware':((.64,.57,.43),.38,0),
    'shop_paper':((.68,.60,.43),.92,0),
    'shop_tin':((.22,.24,.23),.36,.75),
    'shop_cork':((.25,.16,.085),.95,0),
    'shop_wood':((.38,.27,.17),.83,0)}
mesh=bpy.data.meshes.new('Exact staged display');mesh.from_pydata(points,[],faces);mesh.update()
obj=bpy.data.objects.new('Actual shelf and goods geometry',mesh);bpy.context.collection.objects.link(obj)
keys=sorted(set(paints))
for key in keys:obj.data.materials.append(material(key,*palette[key]))
uv=mesh.uv_layers.new(name='UVMap')
for i,poly in enumerate(mesh.polygons):
    poly.material_index=keys.index(paints[i]);poly.use_smooth=paints[i].startswith(('shop_bottle','shop_stoneware','shop_tin'))
    for loop in poly.loop_indices:uv.data[loop].uv=uvs[loop]
mesh.normals_split_custom_set(ns)
wood=bpy.data.images.load(str(ROOT/'Assets/materials/belltower/scans/brown_planks_03_diffuse_4k.png'),check_existing=True)
for key in ('shop_wood',):
    mat=obj.data.materials[keys.index(key)];tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=wood
    multiply=mat.node_tree.nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1
    multiply.inputs[2].default_value=(*palette[key][0],1)
    mat.node_tree.links.new(tex.outputs['Color'],multiply.inputs[1])
    mat.node_tree.links.new(multiply.outputs[0],mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])

red=material('Example existing frame',(.24,.055,.045),.66)
plaster=material('Example facade',(.44,.25,.19),.91)
def box(name,centre,size,mat,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=tuple(v*scale for v in centre));o=bpy.context.object;o.name=name
    o.dimensions=tuple(v*scale for v in size);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    if bevel:mod=o.modifiers.new('Edge profile','BEVEL');mod.width=bevel*scale;mod.segments=2
    return o
w=record['width'];h=record['height']
for x in (-w/2+2,w/2-2):box('Existing side frame',(x,-1.0,h/2),(4,4,h),red,.08)
for z in (h-2,):box('Existing horizontal frame',(0,-1,z),(w-8,4,4),red,.08)
box('Existing lower panel',(0,-2,12),(w,4,24),red,.08)
box('Existing central mullion',(0,-1,h/2),(4,3,h-8),red,.07)
box('Existing crossbar',(0,-1.2,h*.62),(w-8,3.4,4),red,.07)
for x in (-w/2-12,w/2+12):box('Context facade',(x,3,h/2),(24,12,h+28),plaster)
box('Context head',(0,3,h+8),(w,12,16),plaster)
box('Context base',(0,3,-8),(w,12,16),plaster)

scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.6,.7,.85,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
for loc,power,size in [((-70,-100,160),850,130),((80,-120,80),250,80)]:
    bpy.ops.object.light_add(type='AREA',location=tuple(v*scale for v in loc));light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size*scale
    light.rotation_euler=(Vector((0,20*scale,60*scale))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(28*scale,-160*scale,70*scale));camera=bpy.context.object
camera.rotation_euler=(Vector((0,15*scale,55*scale))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=42;camera.data.clip_end=100
scene.camera=camera;scene.render.resolution_x=1200;scene.render.resolution_y=1050;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ROOT/'output/belltower/shop-displays/construction-preview-v3.png')
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
bpy.ops.render.render(write_still=True)
print(json.dumps({'construction_preview':scene.render.filepath,'actual_staged_triangles_visible':len(faces),'native_engine_capture':False}))
