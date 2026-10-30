"""Read-only room-context render of the saved map, with a temporary location marker."""
from pathlib import Path
import json,hashlib,math,sys,time
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import railhead_render as R
OUT=ROOT/'output/asset-improvement-20261030/column-base/whole-column-review';OUT.mkdir(parents=True,exist_ok=True)
R.SCENE=ROOT/'Assets/scenes/maps/Collider/collider.scene'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[R.SCENE]+[ROOT/'Assets/models/maps/collider'/('collider_'+n+ext)
    for n in ('structure','detail','glass') for ext in ('.obj','.mtl','.vmdl')]
sources={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
EYE=(250.,-150.,420.);TARGET=(-960.,-500.,450.);BASE=(-960.,-500.,0.)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.use_denoising=True
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
cam=R.set_camera(EYE,TARGET,75)

# Find the exact original base triangles in the imported saved structure.
from collections import Counter
from mathutils import Matrix
def key(points):return tuple(sorted(tuple(round(float(v),3) for v in p) for p in points))
private=ROOT/'Assets/models/props/collider/column-base-trial-v1'
review=json.loads((Path(__file__).parent/'review.json').read_text())
for path,h in review['proposalSourceSHA256'].items():assert sha(ROOT/path)==h,path
vertices=[];expected=Counter()
for line in (private/'before.obj').read_text().splitlines():
    if line.startswith('v '):
        vertices.append(R.OBJ_TO_MODEL@Vector(tuple(map(float,line.split()[1:])))+base)
    elif line.startswith('f '):
        expected[key([vertices[int(v.split('/')[0])-1] for v in line.split()[1:]])]+=1
remaining=expected.copy();masked=[]
for obj in list(scene.objects):
    if obj.type!='MESH':continue
    world=obj.matrix_world;mesh=obj.data
    for poly in mesh.polygons:
        if len(poly.vertices)!=3:continue
        first=world@mesh.vertices[poly.vertices[0]].co
        if abs(first.x-base.x)>44.01 or abs(first.y-base.y)>44.01 or not -.01<=first.z<=8.01:continue
        signature=key([world@mesh.vertices[v].co for v in poly.vertices])
        if remaining[signature]:
            remaining[signature]-=1;masked.append((obj,poly.index,poly.material_index))
assert not +remaining and len(masked)==12,('Original base not found in imported saved room',len(masked))
invisible=bpy.data.materials.new('Preview only — hide original base for after');invisible.use_nodes=True
g=invisible.node_tree;g.nodes.clear();transparent=g.nodes.new('ShaderNodeBsdfTransparent');output=g.nodes.new('ShaderNodeOutputMaterial')
g.links.new(transparent.outputs[0],output.inputs['Surface'])
slots={}
for obj,index,old in masked:
    if obj.name not in slots:
        obj.data.materials.append(invisible);slots[obj.name]=len(obj.data.materials)-1
replacement=R.map_model('models/props/collider/column-base-trial-v1/after.vmdl')
for obj in replacement:
    obj.matrix_world=Matrix.Translation(base)@R.OBJ_TO_MODEL;obj.hide_render=True
# Broad view-facing fill approximates indoor bounce for a legible location image.
data=bpy.data.lights.new('Offline wall-bounce approximation','AREA');data.energy=7000000;data.shape='DISK';data.size=1000
o=bpy.data.objects.new(data.name,data);scene.collection.objects.link(o);o.location=eye+Vector((0,0,180))
o.rotation_euler=(base+Vector((0,0,450))-o.location).to_track_quat('-Z','Y').to_euler()

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
s.points[0].co=(*(pin+Vector((0,0,12))),1);s.points[1].co=(*(pin+Vector((0,0,185))),1)
o=bpy.data.objects.new('Locator leader',curve);scene.collection.objects.link(o);o.data.materials.append(mat)
text=bpy.data.curves.new('Column location label','FONT');text.body='THIS COLUMN';text.align_x='CENTER';text.align_y='BOTTOM';text.size=26;text.space_line=1.15
o=bpy.data.objects.new('Locator label only',text);scene.collection.objects.link(o);o.location=pin+Vector((0,0,195))
o.rotation_euler=cam.rotation_euler;o.data.materials.append(mat)

scene.render.image_settings.file_format='PNG'
from bpy_extras.object_utils import world_to_camera_view
bpy.context.view_layer.update()
projected=[]
for dx in (-44.,44.):
    for dy in (-44.,44.):
        for z in (0.,900.):
            q=world_to_camera_view(scene,cam,R.plan_to_world((BASE[0]+dx,BASE[1]+dy,z)))
            assert .01<=q.x<=.99 and .01<=q.y<=.99 and q.z>0,('Whole column not in frame',tuple(q))
            projected.append(list(q))
images=[]
for variant in ('before','after'):
    for obj,index,old in masked:obj.data.polygons[index].material_index=old if variant=='before' else slots[obj.name]
    for obj in replacement:obj.hide_render=variant!='after'
    path=OUT/(variant+'-whole-column.png');scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    images.append({'variant':variant,'file':path.name,'sha256':sha(path)})
for path,h in sources.items():assert sha(ROOT/path)==h,path
for path,h in review['proposalSourceSHA256'].items():assert sha(ROOT/path)==h,path
report={'nativeEngineScreenshot':False,'savedMapGeometry':True,'proposalInstalled':False,
    'locationMarkerIsIllustrativeOnly':True,'wholeColumnInFrame':True,'columnPlanZRange':[0,900],
    'sameCameraLightingAndScale':True,'onlyBaseSwappedInRender':True,'oldBaseFaces':12,'newBaseTriangles':35002,
    'eyePlan':EYE,'targetPlan':TARGET,'basePlan':BASE,'horizontalFov':75,'resolution':[1600,1100],
    'CPUThreads':2,'GPUUsed':False,'samples':16,'models':models,'pointLightsUsed':len(points),
    'indirectLightingApproximate':True,'sourceSHA256':sources,'proposalModelSHA256':review['models'],
    'projectedColumnCorners':projected,'images':images}
(OUT/'comparison-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('Whole-column comparison complete; saved map and both proposal models unchanged.',flush=True)
