"""Review one Riverdale reel using the approved, unchanged Railhead resource."""
from pathlib import Path
import sys,json,hashlib,collections,re
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_map as R
import riverdale_yard as Y
OUT=ROOT/'output/riverdale/sand-bin-v1';STAGE=OUT/'stage';RES='models/maps/riverdale/sand-bin-v1';MODEL=STAGE/'Assets'/RES
MODEL.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=list((ROOT/'Assets/models/maps/riverdale').rglob('*'))+list((ROOT/'Assets/materials/riverdale').rglob('*'))+list((ROOT/'Assets/models/maps/boxyard/traffic_cone_v2').rglob('*'))+list((ROOT/'Assets/models/maps/boxyard/traffic_cone_v2').rglob('*'))+[ROOT/'Assets/scenes/maps/Riverdale/riverdale.scene',ROOT/'Tools/riverdale_map.py',ROOT/'Tools/riverdale_yard.py',ROOT/'Tools/railhead_cable_drum.py']
if not (OUT/'source-guard.json').exists():
 (OUT/'source-guard.json').write_text(json.dumps({str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c') and 'sand-bin-v1' not in p.parts},indent=2))
audit=dict(target='Court sand bin at (-1250,258)',existing_improvement_found=False,checked=['Sources and docs for sand_bin/grit_bin','Asset filenames for sand/grit models','Existing Boxyard wheelie bin and Railhead station bin upgrades'],findings=['No existing sand/grit bin replacement found','Wheelie bin and station bin shapes are different functional props','Live bin is still the original box and flat lid'],reuse=['Original yellow finish and SAND label atlas'])
(OUT/'existing-upgrade-audit.json').write_text(json.dumps(audit,indent=2))
legacy=K.Model();Y.sand_bin(legacy,'court sand',(-1250,258),(0,1));R.configure(legacy);K.write_obj(OUT/'legacy-body.obj',legacy,'legacy_body')
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
content=''.join(l for i,l in enumerate(lines) if i not in removed);content=re.sub(r'(?m)^mtllib .+$','mtllib yard_without_bin.mtl',content)
(MODEL/'yard_without_bin.obj').write_text(content);(MODEL/'yard_without_bin.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'yard_without_bin.vmdl').write_text(text.replace('models/maps/riverdale/riverdale_yard_props.obj',RES+'/yard_without_bin.obj'))
from model import model
candidate=model();triangles=K.write_model(MODEL,RES,'sand_bin',candidate)
placement=dict(resource=RES+'/sand_bin.vmdl')
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=triangles,original_triangles=len(removed),source=str(source.relative_to(ROOT)).replace('\\','/'),source_sha256=sha(source),existing_upgrade_checked=True,reused_resource=None,review_only=True,placement=placement),indent=2))
# Adapt the proven native runtime harness; only preview base files are imported.
prior=ROOT/'Sources/Railhead/taxi-post-v1'
for filename in ('native.py','capture.py','import.cs.txt','review.py','runtime_review.cs.txt'):
 t=(prior/filename).read_text().replace('railhead/taxi-post-v1','riverdale/sand-bin-v1').replace('maps/railhead/railhead.scene','maps/riverdale/riverdale.scene').replace('Railhead','Riverdale').replace('railhead-taxi-post','riverdale-shared-reel')
 if filename=='import.cs.txt':t=t.replace('Assets/materials/railhead/taxi-post-v1/','Assets/materials/riverdale/sand-bin-v1/')
 if filename=='review.py':
  t=t.replace("('taxi_post','east_without_taxi')","('sand_bin','yard_without_bin')")
 if filename=='runtime_review.cs.txt':
  t=t.replace('Riverdale taxi post review','Riverdale shared cable reel review').replace('Candidate taxi post failed to load','Shared cable reel failed to load')
  t=t.replace('models/maps/railhead/railhead_dress_east.vmdl','models/maps/riverdale/riverdale_yard_props.vmdl').replace('models/maps/riverdale/sand-bin-v1/taxi_post.vmdl',RES+'/sand_bin.vmdl').replace('east_without_taxi.vmdl','yard_without_bin.vmdl')
  start=t.index(' var views=new[]{');end=t.index('\n foreach(var variant',start)
  t=t[:start]+''' var views=new[]{
 new {Name="bin",Eye=new Vector3(318,1295,45),Target=new Vector3(258,1250,14),Fov=38f,Width=1200,Height=900},
 new {Name="detail",Eye=new Vector3(305,1213,43),Target=new Vector3(258,1250,19),Fov=38f,Width=1200,Height=900}};'''+t[end:]
 (HERE/filename).write_text(t)
print(json.dumps(dict(reused_resource=None,triangles=triangles,old_body_triangles=len(removed),tail_faces_preserved=sum(tail.values()),private_preview_files=len(files))))
