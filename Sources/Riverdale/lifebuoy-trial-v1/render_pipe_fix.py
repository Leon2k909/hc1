"""Matched offline visual check of the exact verified pipe sources; no game/editor capture."""
from pathlib import Path
import sys,json,hashlib
import bpy
from mathutils import Vector
ROOT=Path.cwd();HERE=ROOT/'Sources/Riverdale/lifebuoy-trial-v1';OUT=ROOT/'output/asset-improvement-20261031/riverdale-lifebuoy'
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'Tools'))
import geometry as G,belltower_render as R,riverdale_splice as S
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
shader,kv=R.parse_vmat('materials/riverdale/rv_pipe.vmat');material=R.standard_material('Installed pipe jacketing',kv)
p=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
if kv.get('F_METALNESS_TEXTURE')=='1':
    t=material.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(ROOT/'Assets'/kv['TextureMetalness']));t.image.colorspace_settings.name='Non-Color';material.node_tree.links.new(t.outputs['Color'],p.inputs['Metallic'])
def load(name,path):
    faces=S.read_obj(path)[1];vs=[];uv=[];ns=[];fs=[]
    for paint,corners in faces:
        pos=[tuple(map(float,c[0].split())) for c in corners]
        # Only the west-wall bypass; the long tube legs deliberately extend
        # outside the image rather than introducing artificial cut caps.
        if max(p[0] for p in pos)<900 or min(p[0] for p in pos)>1005:continue
        if max(p[2] for p in pos)<50 or min(p[2] for p in pos)>430:continue
        fs.append(tuple(range(len(vs),len(vs)+len(corners))))
        for point,tex,normal in corners:
            a,z,n=map(float,point.split());vs.append((n-220,a-1000,z-240));uv.append(tuple(map(float,tex.split())))
            a,z,n=map(float,normal.split());ns.append((n,a,z))
    o=G.mesh(name,vs,fs,material,True,uv,False);o.data.normals_split_custom_set_from_vertices(ns);return o
risers=load('Verified unchanged risers',OUT/'checked-risers.obj')
before=load('Actual old service route',OUT/'pipes-before.obj');after=load('Installed bypass route',OUT/'pipes-after.obj')
wall=bpy.data.materials.new('Neutral wall for offline check');wall.diffuse_color=(.28,.29,.29,1);wall.use_nodes=True;wall.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.88
G.box('Studio wall',(0,.6,0),(1400,1.2,1600),wall,0)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.cycles.max_bounces=5;scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
scene.world=scene.world or bpy.data.worlds.new('Offline studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.4,.44,.5,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
target=Vector((25,-40,0))*.0254
for name,at,power,size in [('Broad key',(-2,-4,6),1800,5),('Fill',(4,-3,2),850,4)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=at;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('Matched pipe camera');cam=bpy.data.objects.new('Matched pipe camera',d);bpy.context.collection.objects.link(cam);scene.camera=cam
cam.location=Vector((-190,-255,150))*.0254;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=7.3
report={'offlineRender':True,'nativeEngineScreenshot':False,'sameCameraLightingExposure':True,'images':[]}
for variant in ('before','after'):
    before.hide_render=variant!='before';after.hide_render=variant!='after';path=OUT/f'pipe-{variant}.png';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    report['images'].append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(OUT/'pipe-render-validation.json').write_text(json.dumps(report,indent=2))
