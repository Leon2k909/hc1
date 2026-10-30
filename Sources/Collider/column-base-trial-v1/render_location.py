"""Read-only room-context render of the saved map, with a temporary location marker."""
from pathlib import Path
import json,hashlib,math,sys,time
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import railhead_render as R
OUT=ROOT/'output/asset-improvement-20261030/column-base/location-review';OUT.mkdir(parents=True,exist_ok=True)
R.SCENE=ROOT/'Assets/scenes/maps/Collider/collider.scene'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[R.SCENE]+[ROOT/'Assets/models/maps/collider'/('collider_'+n+ext)
    for n in ('structure','detail','glass') for ext in ('.obj','.mtl','.vmdl')]
sources={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
EYE=(-250.,-320.,95.);TARGET=(-960.,-500.,165.);BASE=(-960.,-500.,0.)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.cycles.max_bounces=5;scene.cycles.diffuse_bounces=2;scene.cycles.glossy_bounces=2;scene.cycles.transparent_max_bounces=8
scene.render.threads_mode='FIXED';scene.render.threads=2
scene.render.use_simplify=True;scene.cycles.texture_limit_render='1024'
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.75
scene.world=bpy.data.worlds.new('Location-view ambient');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.12,.15,.20,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
original_image=R.image
def limited_image(path,data=False):
    img=original_image(path,data)
    if img and max(img.size)>1024:
        factor=1024/max(img.size);img.scale(max(1,int(img.size[0]*factor)),max(1,int(img.size[1]*factor)))
    return img
R.image=limited_image
found=R.read_scene();models=[]
allowed={'models/maps/collider/collider_structure.vmdl','models/maps/collider/collider_detail.vmdl','models/maps/collider/collider_glass.vmdl'}
for path,world,tint in found['models']:
    path=path.get('Path','') if isinstance(path,dict) else path
    if path not in allowed and 'automatic-door-v1' not in path:continue
    copies=R.map_model(path)
    for obj in copies:obj.matrix_world=world@R.OBJ_TO_MODEL
    models.append({'resource':path,'objects':len(copies),'faces':sum(len(o.data.polygons) for o in copies)})
    print('Loaded '+path,flush=True)
base=R.plan_to_world(BASE);eye=R.plan_to_world(EYE)
points=sorted(found['points'],key=lambda p:(p[0].to_translation()-base).length)[:28]
for world,color,radius in points:R.add_point(world,color,radius)
# Broad fill stands in for the saved engine's indirect-light volume.
data=bpy.data.lights.new('Offline indirect-light approximation','AREA');data.energy=1800000
data.shape='DISK';data.size=800
obj=bpy.data.objects.new(data.name,data);scene.collection.objects.link(obj)
obj.location=R.plan_to_world((-750,-320,520));obj.rotation_euler=(base+Vector((0,0,100))-obj.location).to_track_quat('-Z','Y').to_euler()
cam=R.set_camera(EYE,TARGET,90)
# Marker geometry is created only in this render scene, never in game assets.
mat=bpy.data.materials.new('Location marker only');mat.use_nodes=True
nodes=mat.node_tree.nodes;nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission')
em.inputs['Color'].default_value=(1.,.43,.025,1);em.inputs['Strength'].default_value=2.
mat.node_tree.links.new(em.outputs[0],out.inputs['Surface'])
bpy.ops.mesh.primitive_torus_add(major_radius=72,minor_radius=2.2,major_segments=64,minor_segments=8,location=base+Vector((0,0,2.5)))
ring=bpy.context.object;ring.name='LOCATOR ONLY — proposed base position';ring.data.materials.append(mat)
toward=eye-base;toward.z=0;toward.normalize()
pin=base+toward*85
curve=bpy.data.curves.new('Locator leader','CURVE');curve.dimensions='3D';curve.bevel_depth=1.3;curve.bevel_resolution=2
s=curve.splines.new('POLY');s.points.add(1)
s.points[0].co=(*(pin+Vector((0,0,12))),1);s.points[1].co=(*(pin+Vector((0,0,112))),1)
o=bpy.data.objects.new('Locator leader',curve);scene.collection.objects.link(o);o.data.materials.append(mat)
text=bpy.data.curves.new('Column location label','FONT');text.body='THIS COLUMN\nBASE BELOW';text.align_x='CENTER';text.align_y='BOTTOM';text.size=18;text.space_line=1.15
o=bpy.data.objects.new('Locator label only',text);scene.collection.objects.link(o);o.location=pin+Vector((0,0,120))
o.rotation_euler=cam.rotation_euler;o.data.materials.append(mat)
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'room-location.png')
bpy.ops.render.render(write_still=True)
for path,h in sources.items():assert sha(ROOT/path)==h,path
report={'nativeEngineScreenshot':False,'savedMapGeometry':True,'proposalInstalled':False,'locationMarkerIsIllustrativeOnly':True,
    'eyePlan':EYE,'targetPlan':TARGET,'basePlan':BASE,'horizontalFov':90,'resolution':[1600,900],
    'CPUThreads':2,'GPUUsed':False,'samples':24,'models':models,'pointLightsUsed':len(points),
    'indirectLightingApproximate':True,'sourceSHA256':sources,'imageSHA256':sha(OUT/'room-location.png')}
(OUT/'location-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('Location render complete; saved scene and model files unchanged.',flush=True)
