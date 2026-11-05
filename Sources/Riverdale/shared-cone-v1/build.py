"""Review one Riverdale reel using the approved, unchanged Railhead resource."""
from pathlib import Path
import sys,json,hashlib,collections,re
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_map as R
import riverdale_yard as Y
OUT=ROOT/'output/riverdale/shared-cone-v1';STAGE=OUT/'stage';RES='models/maps/riverdale/shared-cone-v1';MODEL=STAGE/'Assets'/RES
MODEL.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=list((ROOT/'Assets/models/maps/riverdale').rglob('*'))+list((ROOT/'Assets/materials/riverdale').rglob('*'))+list((ROOT/'Assets/models/maps/boxyard/traffic_cone_v2').rglob('*'))+list((ROOT/'Assets/models/maps/boxyard/traffic_cone_v2').rglob('*'))+[ROOT/'Assets/scenes/maps/Riverdale/riverdale.scene',ROOT/'Tools/riverdale_map.py',ROOT/'Tools/riverdale_yard.py',ROOT/'Tools/railhead_cable_drum.py']
if not (OUT/'source-guard.json').exists():
 (OUT/'source-guard.json').write_text(json.dumps({str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c') and 'shared-cone-v1' not in p.parts},indent=2))
audit=dict(target='North lane cone at (300,2433)',reuse='models/maps/boxyard/traffic_cone_v2/traffic_cone.vmdl',existing_improvement_found=True,checked=['Boxyard traffic_cone_v2 approved and installed README','Riverdale live cone helper','Sources and notes for cone upgrades'],findings=['Riverdale still uses fourteen-sided solid cones','Approved Boxyard cone has hollow tip and underside, shaped rubber base, wear and three LODs','Reuse unchanged model and material, no duplicate replacement sources'])
(OUT/'existing-upgrade-audit.json').write_text(json.dumps(audit,indent=2))
legacy=K.Model();Y.cone(legacy,'lane cone 0',(300,2433));R.configure(legacy);K.write_obj(OUT/'legacy-body.obj',legacy,'legacy_body')
K.write_obj(OUT/'legacy-full.obj',legacy,'legacy_full')
def records(path):
 lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
 paint='';result=[]
 for i,l in enumerate(lines):
  if l.startswith('usemtl '):paint=l.split()[1]
  if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
 return lines,result
_,old=records(OUT/'legacy-body.obj');body=collections.Counter(key for _,key in old);wanted=body.copy()
_,oldfull=records(OUT/'legacy-full.obj');tail=collections.Counter(key for _,key in oldfull)-body
public=ROOT/'Assets/models/maps/riverdale/riverdale_yard_props.vmdl';text=public.read_text();source=ROOT/'Assets/models/maps/riverdale/riverdale_yard_props.obj'
assert 'filename = "models/maps/riverdale/riverdale_yard_props.obj"' in text
lines,faces=records(source);removed=set()
for i,key in faces:
 if wanted[key]:removed.add(i);wanted[key]-=1
assert not +wanted,('Live body differs from helper',len(+wanted))
kept=collections.Counter(key for i,key in faces if i not in removed)
assert not tail-kept,'Loose cable tail must remain intact'
content=''.join(l for i,l in enumerate(lines) if i not in removed);content=re.sub(r'(?m)^mtllib .+$','mtllib yard_without_cone.mtl',content)
(MODEL/'yard_without_cone.obj').write_text(content);(MODEL/'yard_without_cone.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'yard_without_cone.vmdl').write_text(text.replace('models/maps/riverdale/riverdale_yard_props.obj',RES+'/yard_without_cone.obj'))
radial=1.;axial=1.;scale=[1.,1.,1.];origin=[2433.,-300.,0.]
placement=dict(resource=audit['reuse'],world_scale=scale,world_position=origin,target_center=origin,rotation=[0,0,0],tail_faces_preserved=0)
(OUT/'placement.json').write_text(json.dumps(placement,indent=2))
shared=ROOT/'Assets'/audit['reuse'];triangles=sum(l.startswith('f ') for l in shared.with_name('traffic_cone_lod0.obj').read_text().splitlines())
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=triangles,original_triangles=len(removed),source=str(source.relative_to(ROOT)).replace('\\','/'),source_sha256=sha(source),existing_upgrade_checked=True,reused_resource=audit['reuse'],review_only=True,placement=placement),indent=2))
# Adapt the proven native runtime harness; only preview base files are imported.
prior=ROOT/'Sources/Railhead/taxi-post-v1'
for filename in ('native.py','capture.py','import.cs.txt','review.py','runtime_review.cs.txt'):
 t=(prior/filename).read_text().replace('railhead/taxi-post-v1','riverdale/shared-cone-v1').replace('maps/railhead/railhead.scene','maps/riverdale/riverdale.scene').replace('Railhead','Riverdale').replace('railhead-taxi-post','riverdale-shared-reel')
 if filename=='import.cs.txt':t=t.replace('Assets/materials/railhead/taxi-post-v1/','Assets/materials/riverdale/shared-cone-v1/')
 if filename=='review.py':
  t=t.replace("('taxi_post','east_without_taxi')","('yard_without_cone',)")
 if filename=='runtime_review.cs.txt':
  t=t.replace('Riverdale taxi post review','Riverdale shared cable reel review').replace('Candidate taxi post failed to load','Shared cable reel failed to load')
  t=t.replace('models/maps/railhead/railhead_dress_east.vmdl','models/maps/riverdale/riverdale_yard_props.vmdl').replace('models/maps/riverdale/shared-cone-v1/taxi_post.vmdl',audit['reuse']).replace('east_without_taxi.vmdl','yard_without_cone.vmdl')
  anchor='if(replacement.Model.IsError)'
  t=t.replace(anchor,f'replacement.WorldScale=new Vector3({radial:.9f}f,{axial:.9f}f,{radial:.9f}f);\n  replacement.WorldPosition=new Vector3({origin[0]:.9f}f,{origin[1]:.9f}f,{origin[2]:.9f}f);\n  '+anchor)
  start=t.index(' var views=new[]{');end=t.index('\n foreach(var variant',start)
  t=t[:start]+''' var views=new[]{
 new {Name="cone",Eye=new Vector3(2375,-343,36),Target=new Vector3(2433,-300,13),Fov=33f,Width=1200,Height=900},
 new {Name="detail",Eye=new Vector3(2394,-326,24),Target=new Vector3(2433,-300,13),Fov=33f,Width=1200,Height=900}};'''+t[end:]
 (HERE/filename).write_text(t)
print(json.dumps(dict(reused_resource=audit['reuse'],triangles=triangles,old_body_triangles=len(removed),tail_faces_preserved=sum(tail.values()),private_preview_files=len(files))))
