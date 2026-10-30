"""Matched Cycles renders of the actual before/after OBJs, not engine screenshots."""
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import math
import re
import sys
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import belltower_render as R

OUT=ROOT/'output/asset-improvement-20261029/west-cabinet'
RESOURCE='models/props/collider/west-cabinet-trial-v1'
ASSETS=ROOT/'Assets'
SCALE=.0254
material_cache={}


def material(path):
    if path in material_cache:return material_cache[path]
    shader,keys=R.parse_vmat(path)
    colour=keys.get('TextureColor','')
    if colour.startswith('['):
        c=R.floats(colour);t=R.floats(keys.get('g_vColorTint','[1 1 1 1]'))
        keys={**keys,'g_vColorTint':'['+' '.join(str(c[i]*t[i]) for i in range(3))+' 1]'}
    mat=R.standard_material(path,keys)
    rough=keys.get('TextureRoughness','')
    if rough.startswith('['):
        value=R.floats(rough)[0]
        for node in mat.node_tree.nodes:
            if node.type=='BSDF_PRINCIPLED':node.inputs['Roughness'].default_value=value
    material_cache[path]=mat
    return mat


def model(name):
    directory=ASSETS/RESOURCE
    if name=='before' and not (directory/'before.obj').exists():
        directory=ROOT/'output/collider-cabinet-accepted-20261029/retired-before-resources'
    doc=(directory/(name+'.vmdl')).read_text()
    remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc))
    vertices=[];texcoords=[];normals=[];paint=''
    groups=defaultdict(list)
    for line in (directory/(name+'.obj')).read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vertices.append((-a*SCALE,n*SCALE,z*SCALE))
        elif line.startswith('vt '):texcoords.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);normals.append((-a,n,z))
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f '):groups[paint].append([[int(v)-1 for v in token.split('/')] for token in line.split()[1:]])
    objects=[]
    for paint,faces in groups.items():
        vs=[];uv=[];ns=[];indices=[]
        for triangle in faces:
            indices.append(tuple(range(len(vs),len(vs)+len(triangle))))
            for v,t,n in triangle:
                vs.append(vertices[v]);uv.append(texcoords[t]);ns.append(normals[n])
        mesh=bpy.data.meshes.new(name+'-'+paint)
        mesh.from_pydata(vs,[],indices);mesh.update()
        layer=mesh.uv_layers.new(name='UVMap')
        for loop in mesh.loops:layer.data[loop.index].uv=uv[loop.vertex_index]
        for poly in mesh.polygons:poly.use_smooth=True
        mesh.normals_split_custom_set_from_vertices(ns)
        obj=bpy.data.objects.new(name+'-'+paint,mesh);bpy.context.collection.objects.link(obj)
        obj.data.materials.append(material(remaps[paint+'.vmat']))
        objects.append(obj)
    return objects


bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
before=model('before');after=model('after')
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.cycles.max_bounces=5;scene.cycles.transparent_max_bounces=4
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1000;scene.render.resolution_y=1300;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0.
scene.world=scene.world or bpy.data.worlds.new('Matched studio')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.38,.42,.48,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.005))
floor=bpy.context.object;floor.name='Same neutral preview floor'
mat=bpy.data.materials.new('Neutral matte floor');mat.use_nodes=True
principled=mat.node_tree.nodes.get('Principled BSDF')
principled.inputs['Base Color'].default_value=(.115,.125,.14,1);principled.inputs['Roughness'].default_value=.78
floor.data.materials.append(mat)
for name,position,power,size,color in (
    ('Key',(-3.2,-3.7,5.5),950,4.0,(1.,.91,.82)),
    ('Fill',(4.,-1.0,3.0),620,3.4,(.80,.88,1.)),
    ('Rim',(-.5,3.5,4.8),1150,3.0,(.94,.97,1.))):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    light=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(light)
    light.location=position;light.rotation_euler=(Vector((0,0,1.7))-light.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Matched 54 mm camera');camera=bpy.data.objects.new('Matched camera',data)
bpy.context.collection.objects.link(camera);scene.camera=camera
data.lens=54.;data.clip_end=1000
views=[('main',(3.1,-4.7,3.2),(0,0,1.72))]
report={'renderer':'Blender Cycles','nativeEngineScreenshot':False,'sameCameraLightingScaleAndExposure':True,
    'samples':scene.cycles.samples,'viewTransform':'AgX','exposure':0.,'images':[]}
for view,eye,target in views:
    camera.location=eye;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    data.lens=48.
    for variant,objects in (('before',before),('after',after)):
        for obj in before:obj.hide_render=variant!='before'
        for obj in after:obj.hide_render=variant!='after'
        path=OUT/(variant+'-'+view+'.png')
        scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True)
        report['images'].append({'variant':variant,'view':view,'file':path.name,'eyeMetres':eye,'targetMetres':target,
            'lens':data.lens,'width':scene.render.resolution_x,'height':scene.render.resolution_y,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(OUT/'render-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
