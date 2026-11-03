"""Matched renders of exported geometry and engine texture maps. No generated concept image."""
from pathlib import Path
from collections import defaultdict
import math, json, re, sys, hashlib
import bpy
from mathutils import Vector

WORK=Path(__file__).resolve().parent
ASSETS=WORK/'candidate/Assets'
OUT=WORK.parent/'outputs'
OUT.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
cache={}

def material(path):
    if path in cache:return cache[path]
    text=(ASSETS/path).read_text();keys=dict(re.findall(r'^\s*(\w+)\s+"([^"]*)"',text,re.M))
    mat=bpy.data.materials.new(path);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;p=nodes.get('Principled BSDF')
    p.inputs['Metallic'].default_value=float(keys.get('g_flMetalness',0))
    for key,socket,color in (('TextureColor','Base Color',True),('TextureRoughness','Roughness',False),('TextureNormal','Normal',False)):
        file=ASSETS/keys.get(key,'')
        if not file.is_file():continue
        img=bpy.data.images.load(str(file),check_existing=True)
        img.colorspace_settings.name='sRGB' if color else 'Non-Color'
        node=nodes.new('ShaderNodeTexImage');node.image=img;node.extension='REPEAT'
        if key=='TextureNormal':
            normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=1
            links.new(node.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],p.inputs[socket])
        else:links.new(node.outputs['Color'],p.inputs[socket])
    cache[path]=mat
    return mat

def model(folder,label):
    directory=ASSETS/folder;doc=(directory/'after.vmdl').read_text()
    remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc))
    vs=[];uv=[];ns=[];groups=defaultdict(list);paint=''
    for line in (directory/'after.obj').read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vs.append((-a*.0254,n*.0254,z*.0254))
        elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);ns.append((-a,n,z))
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f '):groups[paint].append([[int(v)-1 for v in token.split('/')] for token in line.split()[1:]])
    result=[]
    for paint,faces in groups.items():
        vv=[];tt=[];nn=[];ff=[]
        for face in faces:
            ff.append(tuple(range(len(vv),len(vv)+len(face))))
            for v,t,n in face:vv.append(vs[v]);tt.append(uv[t]);nn.append(ns[n])
        mesh=bpy.data.meshes.new(label+' '+paint);mesh.from_pydata(vv,[],ff);mesh.update()
        layer=mesh.uv_layers.new(name='UVMap')
        for loop in mesh.loops:layer.data[loop.index].uv=tt[loop.vertex_index]
        for poly in mesh.polygons:poly.use_smooth=True
        mesh.normals_split_custom_set_from_vertices(nn)
        obj=bpy.data.objects.new(label+' '+paint,mesh);bpy.context.collection.objects.link(obj)
        obj.data.materials.append(material(remaps[paint+'.vmat']));result.append(obj)
    return result

before=model('models/props/collider/chair-trial-v1','Before')
after=model('models/props/collider/chair-realism-v2','After')
scene=bpy.context.scene;scene.render.engine='CYCLES'
scene.cycles.device='CPU';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.cycles.max_bounces=6;scene.cycles.transparent_max_bounces=4
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1100;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
scene.world=scene.world or bpy.data.worlds.new('Shared studio')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.32,.37,.43,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.30
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.001))
floor=bpy.context.object;floor.name='Shared neutral floor'
mat=bpy.data.materials.new('Floor');mat.use_nodes=True
p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.10,.112,.128,1);p.inputs['Roughness'].default_value=.82
floor.data.materials.append(mat)
for name,eye,power,size,color in (
    ('Key',(-3.2,-3.7,5.5),950,3.4,(1.,.93,.86)),
    ('Fill',(4.,-1.,3),620,3.4,(.84,.91,1.)),
    ('Rim',(-.5,3.5,4.8),1150,3,(.96,.98,1.))):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob);ob.location=eye
    ob.rotation_euler=(Vector((0,0,.85))-ob.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Matched camera');camera=bpy.data.objects.new('Matched camera',data)
bpy.context.collection.objects.link(camera);scene.camera=camera;data.clip_end=1000
views=[('whole',(1.3,-2.1,1.45),(0,0,.64),60),('detail',(.92,-1.55,1.15),(0,-.02,.89),77)]
if '--quick' in sys.argv:
    scene.render.resolution_percentage=60;scene.cycles.samples=16;views=views[:1]
report={'renderer':'Blender Cycles','nativeEngineScreenshot':False,'sameCameraLightingScaleExposure':True,'baseline':'current after.vmdl, not the retired original block chair','images':[]}
for view,eye,target,lens in views:
    camera.location=eye;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();data.lens=lens
    for variant in ('before','after'):
        for ob in before:ob.hide_render=variant!='before'
        for ob in after:ob.hide_render=variant!='after'
        name=f'{variant}-{view}'+('-quick' if '--quick' in sys.argv else '')+'.png'
        path=OUT/name;scene.render.filepath=str(path)
        if not (variant=='before' and '--reuse-before' in sys.argv and path.exists()):
            bpy.ops.render.render(write_still=True)
        report['images'].append({'file':name,'camera':eye,'target':target,'lens':lens,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        print('COMPLETED '+name,flush=True)
(OUT/'render-report.json').write_text(json.dumps(report,indent=2))
# Persist the exact material setup and both variants for further review.
if '--quick' not in sys.argv:
    for ob in before:ob.hide_render=True
    for ob in after:ob.hide_render=False
    camera.location=views[0][1];camera.rotation_euler=(Vector(views[0][2])-camera.location).to_track_quat('-Z','Y').to_euler();data.lens=views[0][3]
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'candidate/chair-review.blend'))
print('RENDER_COMPLETE',flush=True)
