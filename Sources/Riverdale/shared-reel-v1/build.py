"""Review one Riverdale reel using the approved, unchanged Railhead resource."""
from pathlib import Path
import sys,json,hashlib,collections,re
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_map as R
import riverdale_yard as Y
OUT=ROOT/'output/riverdale/shared-reel-v1';STAGE=OUT/'stage';RES='models/maps/riverdale/shared-reel-v1';MODEL=STAGE/'Assets'/RES
MODEL.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=list((ROOT/'Assets/models/maps/riverdale').rglob('*'))+list((ROOT/'Assets/materials/riverdale').rglob('*'))+list((ROOT/'Assets/models/maps/railhead/cable-drum-v1').rglob('*'))+list((ROOT/'Assets/materials/railhead/cable-drum-v1').rglob('*'))+[ROOT/'Assets/scenes/maps/Riverdale/riverdale.scene',ROOT/'Tools/riverdale_map.py',ROOT/'Tools/riverdale_yard.py',ROOT/'Tools/railhead_cable_drum.py']
if not (OUT/'source-guard.json').exists():
 (OUT/'source-guard.json').write_text(json.dumps({str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c') and 'shared-reel-v1' not in p.parts},indent=2))
audit=dict(target='North-lane reel at plan (60,2420), R20, width26',reuse='models/maps/railhead/cable-drum-v1/cable_drum.vmdl',existing_improvement_found=True,checked=['Sources, notes and Tools for Riverdale reel upgrades','Approved Railhead cable-drum-v1 geometry and original timber finish','Approved Orion cable_reel_v1 model and 4 LODs'],findings=['Riverdale live reel is still the crude 20-sided turned helper','Railhead is a generic wooden reel with real boards, axle bore, rims, fasteners and individual windings','Orion reel has a larger 52-inch diameter and map-specific inventory label; Railhead fits better','No replacement mesh, materials or textures are copied or generated'],preserved=['Original loose cable tail','Original collision and scene','All other Riverdale reels'])
(OUT/'existing-upgrade-audit.json').write_text(json.dumps(audit,indent=2))
# Export only the old body/hubs for exact face matching; retain its pipe tail.
legacy=K.Model();pipe=Y.P.pipe
try:
 Y.P.pipe=lambda *args,**kwargs:None
 Y.cable_reel(legacy,'lane reel',(60,2420),(1,0))
finally:Y.P.pipe=pipe
R.configure(legacy);K.write_obj(OUT/'legacy-body.obj',legacy,'legacy_body')
full=K.Model();Y.cable_reel(full,'lane reel',(60,2420),(1,0));R.configure(full);K.write_obj(OUT/'legacy-full.obj',full,'legacy_full')
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
content=''.join(l for i,l in enumerate(lines) if i not in removed);content=re.sub(r'(?m)^mtllib .+$','mtllib yard_without_reel.mtl',content)
(MODEL/'yard_without_reel.obj').write_text(content);(MODEL/'yard_without_reel.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'yard_without_reel.vmdl').write_text(text.replace('models/maps/riverdale/riverdale_yard_props.obj',RES+'/yard_without_reel.obj'))
radial=40/47.2;axial=28.8/30.8;scale=[radial,axial,radial];origin=[2420-(-1632)*radial,-60-(-1878)*axial,20-23.9*radial]
placement=dict(resource=audit['reuse'],world_scale=scale,world_position=origin,source_center=[-1632,-1878,23.9],target_center=[2420,-60,20],rotation=[0,0,0],tail_faces_preserved=sum(tail.values()))
(OUT/'placement.json').write_text(json.dumps(placement,indent=2))
shared=ROOT/'Assets'/audit['reuse'];triangles=sum(l.startswith('f ') for l in shared.with_suffix('.obj').read_text().splitlines())
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=triangles,original_triangles=len(removed),source=str(source.relative_to(ROOT)).replace('\\','/'),source_sha256=sha(source),existing_upgrade_checked=True,reused_resource=audit['reuse'],review_only=True,placement=placement),indent=2))
# Adapt the proven native runtime harness; only preview base files are imported.
prior=ROOT/'Sources/Railhead/taxi-post-v1'
for filename in ('native.py','capture.py','import.cs.txt','review.py','runtime_review.cs.txt'):
 t=(prior/filename).read_text().replace('railhead/taxi-post-v1','riverdale/shared-reel-v1').replace('maps/railhead/railhead.scene','maps/riverdale/riverdale.scene').replace('Railhead','Riverdale').replace('railhead-taxi-post','riverdale-shared-reel')
 if filename=='import.cs.txt':t=t.replace('Assets/materials/railhead/taxi-post-v1/','Assets/materials/riverdale/shared-reel-v1/')
 if filename=='review.py':
  t=t.replace("('taxi_post','east_without_taxi')","('yard_without_reel',)")
 if filename=='runtime_review.cs.txt':
  t=t.replace('Riverdale taxi post review','Riverdale shared cable reel review').replace('Candidate taxi post failed to load','Shared cable reel failed to load')
  t=t.replace('models/maps/railhead/railhead_dress_east.vmdl','models/maps/riverdale/riverdale_yard_props.vmdl').replace('models/maps/riverdale/shared-reel-v1/taxi_post.vmdl',audit['reuse']).replace('east_without_taxi.vmdl','yard_without_reel.vmdl')
  anchor='if(replacement.Model.IsError)'
  t=t.replace(anchor,f'replacement.WorldScale=new Vector3({radial:.9f}f,{axial:.9f}f,{radial:.9f}f);\n  replacement.WorldPosition=new Vector3({origin[0]:.9f}f,{origin[1]:.9f}f,{origin[2]:.9f}f);\n  '+anchor)
  start=t.index(' var views=new[]{');end=t.index('\n foreach(var variant',start)
  t=t[:start]+''' var views=new[]{
 new {Name="reel",Eye=new Vector3(2345,-145,65),Target=new Vector3(2420,-60,20),Fov=40f,Width=1200,Height=900},
 new {Name="detail",Eye=new Vector3(2380,-118,43),Target=new Vector3(2420,-60,22),Fov=36f,Width=1200,Height=900}};'''+t[end:]
 (HERE/filename).write_text(t)
print(json.dumps(dict(reused_resource=audit['reuse'],triangles=triangles,old_body_triangles=len(removed),tail_faces_preserved=sum(tail.values()),private_preview_files=len(files))))
