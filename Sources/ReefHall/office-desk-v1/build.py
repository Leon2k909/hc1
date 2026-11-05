from pathlib import Path
from collections import Counter
import json,sys,hashlib,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'review';STAGE=OUT/'stage';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_splice as S,reefhall_map as R
import desk as G
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base='Assets/models/maps/reefhall/reefhall_control'
inputs=['Tools/reefhall_map.py','Assets/scenes/maps/ReefHall/reefhall.scene']+[base+'.'+e for e in ('obj','mtl','vmdl')]
inputs += [p.relative_to(ROOT).as_posix() for p in (ROOT/'Assets/models/maps/reefhall').glob('reefhall_control*hulls*.obj')]
guards={k:sha(ROOT/k) for k in inputs}
for rel in inputs:
 p=OUT/'baseline'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
old=G.original(K.Model());new=G.build(K.Model());R.configure(old);R.configure(new)
K.write_obj(OUT/'removed.obj',old,'reefhall_control');removed=Counter(S.read_obj(OUT/'removed.obj')[1])
K.write_obj(OUT/'added.obj',new,'reefhall_control');added=S.read_obj(OUT/'added.obj')[1]
header,public=S.read_obj(ROOT/(base+'.obj'));assert not removed-Counter(public),'Original desk mismatch'
result=list((Counter(public)-removed).elements())+added
folder=STAGE/'Assets/models/maps/reefhall/office-desk-v1';folder.mkdir(parents=True,exist_ok=True)
for variant,m in [('before',old),('desk',new)]:
 K.write_obj(folder/(variant+'.obj'),m,'reefhall_control');K.write_vmdl(folder/(variant+'.vmdl'),'models/maps/reefhall/office-desk-v1',variant,m)
 faces=S.read_obj(folder/(variant+'.obj'))[1];local=[]
 # Undo yaw 180 for the review: OBJ (-e,z,n), then reverse local x/y.
 for mat,corners in faces:
  q=[]
  for p,uv,n in corners:
   a,b,c=map(float,p.split());nx,ny,nz=map(float,n.split())
   q.append((f'{-a-G.CENTRE[0]:.3f} {b-G.Z:.3f} {-c+G.CENTRE[1]:.3f}',uv,f'{-nx:.5f} {ny:.5f} {-nz:.5f}'))
  local.append((mat,tuple(q)))
 S.write_obj(folder/(variant+'.obj'),['mtllib '+variant+'.mtl\n','o '+variant+'\n'],local)
S.write_obj(folder/'control_preview.obj',['mtllib control_preview.mtl\n','o control_preview\n'],result)
(folder/'control_preview.mtl').write_bytes((ROOT/(base+'.mtl')).read_bytes())
text=(ROOT/(base+'.vmdl')).read_bytes().decode().replace('models/maps/reefhall/reefhall_control.obj','models/maps/reefhall/office-desk-v1/control_preview.obj')
(folder/'control_preview.vmdl').write_bytes(text.encode())
assert 'office-desk-v1/control_preview.obj' in text
plan=dict(guards=guards,removed=sum(removed.values()),added=len(added),preserved=len(public)-sum(removed.values()),files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'preview-plan.json').write_text(json.dumps(plan,indent=2));print({k:v for k,v in plan.items() if k not in ('guards','files')})
for file in ('native.py','import_preview.cs.txt'):
 s=(ROOT/'Sources/ReefHall/bronze-planter-v1'/file).read_text().replace('bronze-planter-v1','office-desk-v1')
 (HERE/file).write_text(s)
s=(ROOT/'Sources/ReefHall/bronze-planter-v1/capture.cs.txt').read_text().replace('bronze-planter-v1','office-desk-v1').replace('"before","planter"','"before","desk"')
s=s.replace('W(65,-95,80)','W(95,-125,90)').replace('W(0,0,36)','W(0,0,26)').replace('FieldOfView=40','FieldOfView=42').replace('1000,1150','1200,900')
(HERE/'capture.cs.txt').write_text(s)
s=(ROOT/'Sources/ReefHall/bronze-planter-v1/context.cs.txt').read_text().replace('bronze-planter-v1','office-desk-v1').replace('reefhall_lobby.vmdl','reefhall_control.vmdl').replace('lobby_preview.vmdl','control_preview.vmdl')
s=s.replace('new Vector3(-2775f,-180f,75f)','new Vector3(1860f,865f,287f)').replace('new Vector3(-2885.56f,-98.75f,37f)','new Vector3(1960f,780f,237f)').replace('Fov: 48f','Fov: 54f')
s=s.replace('new Vector3(-2580f,-250f,100f)','new Vector3(1825f,1010f,310f)').replace('new Vector3(-2890f,0f,70f)','new Vector3(2010f,810f,240f)').replace('Fov: 82f','Fov: 75f')
(HERE/'context.cs.txt').write_text(s)
p=OUT/'context';p.mkdir(exist_ok=True);(p/'config.json').write_text('{"phase":"preview","width":1600,"height":1000,"stream_frames":65,"settle_frames":30}')
