"""Render previous and revised real meshes with identical cameras and lighting."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,math,re,sys
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT=Path(__file__).resolve().parents[3]
ASSETS=ROOT/'Assets';SOURCE=ROOT/'Sources/Collider/tool-cabinet-trial-v1'
OUT=ROOT/'output/asset-improvement-20261030/tool-cabinet'
RESOURCE='models/props/collider/tool-cabinet-trial-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
candidate=json.loads((SOURCE/'candidate.json').read_text())
for path,h in candidate['protectedSourceSHA256'].items():assert sha(ROOT/path)==h,path
proposal={p.relative_to(ROOT).as_posix():sha(p) for directory in (ASSETS/RESOURCE,ASSETS/'materials/collider/tool-cabinet-trial-v1') for p in directory.iterdir() if p.is_file() and p.suffix in ('.obj','.mtl','.vmdl','.vmat','.png')}
image_cache={};mat_cache={}

def material(root,path):
    key=(str(root),path)
    if key in mat_cache:return mat_cache[key]
    text=(root/path).read_text();keys=dict(re.findall(r'^\s*(\w+)\s+"([^\"]+)"',text,re.M))
    mat=bpy.data.materials.new(root.parent.name+'-'+Path(path).stem);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;p=nodes.get('Principled BSDF')
    for source,target,data in (('TextureColor','Base Color',False),('TextureRoughness','Roughness',True),('TextureMetalness','Metallic',True),('TextureNormal','Normal',True)):
        value=keys.get(source,'')
        file=root/value
        if value and not value.startswith('[') and file.is_file():
            cache=(str(file),data)
            if cache not in image_cache:
                im=bpy.data.images.load(str(file),check_existing=True)
                if data:im.colorspace_settings.name='Non-Color'
                image_cache[cache]=im
            tex=nodes.new('ShaderNodeTexImage');tex.image=image_cache[cache]
            if target=='Normal':
                nm=nodes.new('ShaderNodeNormalMap');links.new(tex.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],p.inputs['Normal'])
            else:links.new(tex.outputs['Color'],p.inputs[target])
        elif target=='Metallic':p.inputs[target].default_value=float(keys.get('g_flMetalness','0'))
        elif target=='Roughness' and value.startswith('['):p.inputs[target].default_value=float(value.strip('[]').split()[0])
        elif target=='Base Color' and value.startswith('['):p.inputs[target].default_value=tuple(map(float,value.strip('[]').split()[:3]))+(1.,)
    mat_cache[key]=mat;return mat

def model(name,root):
    directory=root/RESOURCE
    remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',(directory/(name+'.vmdl')).read_text()))
    positions=[];uv=[];normals=[];paint='';groups=defaultdict(list)
    for line in (directory/(name+'.obj')).read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);positions.append((-a*.0254,n*.0254,z*.0254))
        elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);normals.append((-a,n,z))
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f '):groups[paint].append([[int(v)-1 for v in token.split('/')] for token in line.split()[1:]])
    objects=[]
    for paint,faces in groups.items():
        vs=[];coords=[];ns=[];triangles=[]
        for f in faces:
            triangles.append(tuple(range(len(vs),len(vs)+len(f))))
            for v,t,n in f:vs.append(positions[v]);coords.append(uv[t]);ns.append(normals[n])
        mesh=bpy.data.meshes.new(name+'-'+paint);mesh.from_pydata(vs,[],triangles);mesh.update()
        layer=mesh.uv_layers.new(name='UVMap')
        for loop in mesh.loops:layer.data[loop.index].uv=coords[loop.vertex_index]
        for polygon in mesh.polygons:polygon.use_smooth=True
        mesh.normals_split_custom_set_from_vertices(ns)
        obj=bpy.data.objects.new(name+'-'+paint,mesh);bpy.context.collection.objects.link(obj)
        obj.data.materials.append(material(root,remaps[paint+'.vmat']));objects.append(obj)
    return objects

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
previous=model('before',ASSETS);revised=model('after',ASSETS)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32
scene.cycles.use_denoising=True;scene.cycles.max_bounces=6;scene.cycles.transparent_max_bounces=4
scene.render.threads_mode='FIXED';scene.render.threads=2
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
scene.world=bpy.data.worlds.new('Identical neutral studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.32,.37,.43,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.22
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.0003))
floor=bpy.context.object;floor.name='Same review floor';mat=bpy.data.materials.new('Floor');mat.use_nodes=True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.105,.115,.13,1)
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.76;floor.data.materials.append(mat)
lights=[]
for name,position,power,size,color in (
    ('Key',(-3.8,-4.2,5.2),1150,2.8,(1,.91,.82)),
    ('Fill',(4.,-1.0,3.0),390,3.1,(.80,.88,1.)),
    ('Rim',(-.5,3.5,4.8),950,2.5,(.94,.97,1.))):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    light=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(light);light.location=position
    light.rotation_euler=(Vector((0,0,.85))-light.location).to_track_quat('-Z','Y').to_euler()
    lights.append({'name':name,'position':position,'power':power,'size':size,'color':color})
data=bpy.data.cameras.new('Matched 54 mm');camera=bpy.data.objects.new('Same camera',data)
bpy.context.collection.objects.link(camera);scene.camera=camera;data.lens=54.;data.clip_end=1000
views=[('main',(3.25,-4.1,2.60),(0,0,.66)),('rear',(-3.4,4.2,2.55),(0,0,.66))]
report={'nativeEngineScreenshot':False,'sameCameraLightingScaleAndExposure':True,'fullObjectInAllViews':True,'fullObjectInComparisonViews':True,
        'previousModelSHA256':sha(ASSETS/RESOURCE/'before.obj'),'revisedModelSHA256':sha(ASSETS/RESOURCE/'after.obj'),
        'CPUThreads':2,'GPUUsed':False,'samples':32,'lights':lights,'resolution':[1600,1200],
        'protectedSourceSHA256':candidate['protectedSourceSHA256'],'proposalSourceSHA256':proposal,'images':[]}
OUT.mkdir(parents=True,exist_ok=True)
for view,eye,target in views:
    camera.location=eye;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()
    if view!='surface':
        for obj in previous+revised:
            for corner in obj.bound_box:
                p=world_to_camera_view(scene,camera,obj.matrix_world@Vector(corner))
                assert .025<p.x<.975 and .025<p.y<.975 and p.z>0,('Cropped',view,obj.name,tuple(p))
    for variant in ('after','before'):
        if view=='rear' and variant=='before':continue
        for obj in previous:obj.hide_render=variant!='before'
        for obj in revised:obj.hide_render=variant!='after'
        path=OUT/(variant+'-'+view+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        report['images'].append({'view':view,'variant':variant,'file':path.name,'eyeMetres':eye,'targetMetres':target,'sha256':sha(path)})
for path,h in {**candidate['protectedSourceSHA256'],**proposal}.items():assert sha(ROOT/path)==h,path
(OUT/'render-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('Matched whole-cabinet comparisons complete; map sources unchanged.',flush=True)
