"""Show the complete column in the saved room; swap only the proposed base in a render."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=ROOT/'output/asset-improvement-20261030/column-base/whole-column-review';OUT.mkdir(parents=True,exist_ok=True)
s=(HERE/'render_location.py').read_text()
s=s.replace('column-base/location-review','column-base/whole-column-review')
s=s.replace("EYE=(-250.,-320.,95.);TARGET=(-960.,-500.,165.);BASE=(-960.,-500.,0.)",
    "EYE=(250.,-150.,420.);TARGET=(-960.,-500.,450.);BASE=(-960.,-500.,0.)")
s=s.replace('resolution_y=900','resolution_y=1100').replace('scene.cycles.samples=24','scene.cycles.samples=16')
s=s.replace("cam=R.set_camera(EYE,TARGET,90)","cam=R.set_camera(EYE,TARGET,75)")
s=s.replace("text.body='THIS COLUMN\\nBASE BELOW'","text.body='THIS COLUMN'")
s=s.replace('text.size=18','text.size=26').replace('Vector((0,0,120))','Vector((0,0,195))')
s=s.replace('Vector((0,0,112))','Vector((0,0,185))')
insert=r'''
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
'''
needle="# Marker geometry is created only in this render scene, never in game assets."
assert needle in s;s=s.replace(needle,insert+'\n'+needle)
start=s.index("scene.render.image_settings.file_format='PNG';")
s=s[:start]+r'''
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
'''
(HERE/'render_whole_column.py').write_text(s)
wrapper=(HERE/'render_low_impact.py').read_text().replace('column-base','column-base/whole-column-review')
wrapper=wrapper.replace("parent/'render.py'","parent/'render_whole_column.py'")
# Only the output path contains column-base in the original wrapper.
assert "column-base/whole-column-review'" in wrapper
(HERE/'render_whole_column_low_impact.py').write_text(wrapper)
print('Prepared full-column room comparison at identical cameras; assets remain untouched.')
