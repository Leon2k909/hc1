from pathlib import Path
from collections import Counter
import json,sys,hashlib,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'review';STAGE=OUT/'stage';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_splice as S,reefhall_map as R
import whale as G
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base='Assets/models/maps/reefhall/reefhall_lobby'
inputs=['Tools/reefhall_map.py','Assets/scenes/maps/ReefHall/reefhall.scene']+[base+'.'+e for e in ('obj','mtl','vmdl')]
inputs += [p.relative_to(ROOT).as_posix() for p in (ROOT/'Assets/models/maps/reefhall').glob('reefhall_lobby*hulls*.obj')]
guards={k:sha(ROOT/k) for k in inputs}
for rel in inputs:
 p=OUT/'baseline'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
original=G.original(K.Model());cables=K.Model();old=K.Model()
cables.polygons['rh_steel']=original.polygons['rh_steel'];old.polygons['rh_bone']=original.polygons['rh_bone']
for m,paint in ((cables,'rh_steel'),(old,'rh_bone')):
 m.polygon_normals.update({k:v for k,v in original.polygon_normals.items() if k[0]==paint})
 m.polygon_uvs.update({k:v for k,v in original.polygon_uvs.items() if k[0]==paint})
new=G.build(K.Model());R.configure(old);R.configure(new);R.configure(cables)
K.write_obj(OUT/'removed.obj',old,'reefhall_lobby');removed=Counter(S.read_obj(OUT/'removed.obj')[1])
K.write_obj(OUT/'added.obj',new,'reefhall_lobby');added=S.read_obj(OUT/'added.obj')[1]
header,public=S.read_obj(ROOT/(base+'.obj'));assert not removed-Counter(public),'Original skeleton mismatch'
result=list((Counter(public)-removed).elements())+added
K.write_obj(OUT/'cables.obj',cables,'reefhall_lobby');cablefaces=S.read_obj(OUT/'cables.obj')[1]
assert not Counter(cablefaces)-Counter(public)
folder=STAGE/'Assets/models/maps/reefhall/whale-skeleton-v1';folder.mkdir(parents=True,exist_ok=True)
e,n=G.CENTRE;z=G.Z
for variant,m in [('before',old),('whale',new)]:
 m.extend(cables);R.configure(m);K.write_obj(folder/(variant+'.obj'),m,'reefhall_lobby');K.write_vmdl(folder/(variant+'.vmdl'),'models/maps/reefhall/whale-skeleton-v1',variant,m)
 faces=S.read_obj(folder/(variant+'.obj'))[1];local=[]
 for mat,corners in faces:
  q=[]
  for p,uv,nrm in corners:
   a,b,c=map(float,p.split());q.append((f'{a+e:.3f} {b-z:.3f} {c-n:.3f}',uv,nrm))
  local.append((mat,tuple(q)))
 S.write_obj(folder/(variant+'.obj'),['mtllib '+variant+'.mtl\n','o '+variant+'\n'],local)
S.write_obj(folder/'lobby_preview.obj',['mtllib lobby_preview.mtl\n','o lobby_preview\n'],result)
(folder/'lobby_preview.mtl').write_bytes((ROOT/(base+'.mtl')).read_bytes())
text=(ROOT/(base+'.vmdl')).read_bytes().decode().replace('models/maps/reefhall/reefhall_lobby.obj','models/maps/reefhall/whale-skeleton-v1/lobby_preview.obj');assert 'whale-skeleton-v1/lobby_preview.obj' in text
(folder/'lobby_preview.vmdl').write_bytes(text.encode())
plan=dict(guards=guards,removed=sum(removed.values()),added=len(added),preserved=len(public)-sum(removed.values()),cablefaces=len(cablefaces),files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'preview-plan.json').write_text(json.dumps(plan,indent=2));print({k:v for k,v in plan.items() if k not in ('guards','files')})
for file in ('native.py','import_preview.cs.txt','direct.py'):
 s=(ROOT/'Sources/Orion/mount-pedestals-v1'/file).read_text().replace('Sources/Orion/mount-pedestals-v1','Sources/ReefHall/whale-skeleton-v1').replace('orion/mount-pedestals-v1','reefhall/whale-skeleton-v1');(HERE/file).write_text(s)
s=(ROOT/'Sources/ReefHall/office-desk-v1/capture.cs.txt').read_text().replace('office-desk-v1','whale-skeleton-v1').replace('"before","desk"','"before","whale"')
s=s.replace('W(95,-125,90)','W(780,400,320)').replace('W(0,0,26)','W(0,80,0)').replace('FieldOfView=42','FieldOfView=58').replace('1200,900','1600,1000').replace('new Vector3(0,0,-.2f)','new Vector3(0,0,-145f)').replace('floor.WorldPosition=new','floor.WorldScale=new Vector3(3,3,1);floor.WorldPosition=new').replace('W(45,-65,100)','W(400,-300,300)').replace('light.Radius=400','light.Radius=3000').replace('frame<65','frame<30')
(HERE/'capture.cs.txt').write_text(s)
s=(ROOT/'Sources/ReefHall/bronze-planter-v1/context.cs.txt').read_text().replace('bronze-planter-v1','whale-skeleton-v1')
s=s.replace('new Vector3(-2775f,-180f,75f)','new Vector3(-2820f,40f,555f)').replace('new Vector3(-2885.56f,-98.75f,37f)','new Vector3(-2300f,75f,475f)').replace('Fov: 48f','Fov: 88f')
s=s.replace('new Vector3(-2580f,-250f,100f)','new Vector3(-1840f,-650f,290f)').replace('new Vector3(-2890f,0f,70f)','new Vector3(-2300f,100f,470f)').replace('Fov: 82f','Fov: 88f')
(HERE/'context.cs.txt').write_text(s);p=OUT/'context';p.mkdir(exist_ok=True);(p/'config.json').write_text(json.dumps(dict(phase='preview',width=1600,height=1000,stream_frames=25,settle_frames=12)))
s=(ROOT/'Sources/ReefHall/office-desk-v1/compile.py').read_text().replace('office-desk-v1','whale-skeleton-v1').replace("('before','desk','control_preview')","('before','whale','lobby_preview')");(HERE/'compile.py').write_text(s)
