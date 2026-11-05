from pathlib import Path
from collections import Counter
import json,sys,hashlib,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'review';STAGE=OUT/'stage';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_splice as S,orion_map as R
import lamp as G
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base='Assets/models/maps/orion/orion_pad'
inputs=['Tools/orion_parts.py','Tools/orion_map.py','Assets/scenes/maps/Orion/orion.scene']+[base+'.'+e for e in ('obj','mtl','vmdl')]
inputs += [p.relative_to(ROOT).as_posix() for p in (ROOT/'Assets/models/maps/orion').glob('orion_pad*hulls*.obj')]
guards={k:sha(ROOT/k) for k in inputs}
for rel in inputs:
 p=OUT/'baseline'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
old=K.Model();new=K.Model()
for c in G.CENTRES:G.original(old,c);G.build(new,c)
R.configure(old);R.configure(new)
K.write_obj(OUT/'removed.obj',old,'orion_pad');removed=Counter(S.read_obj(OUT/'removed.obj')[1])
K.write_obj(OUT/'added.obj',new,'orion_pad');added=S.read_obj(OUT/'added.obj')[1]
header,public=S.read_obj(ROOT/(base+'.obj'));assert not removed-Counter(public),'Original lamps mismatch'
result=list((Counter(public)-removed).elements())+added
folder=STAGE/'Assets/models/maps/orion/mount-lamps-v1';folder.mkdir(parents=True,exist_ok=True)
e,n,z=G.CENTRES[0]
for variant,draw in [('before',G.original),('lamp',G.build)]:
 m=draw(K.Model(),G.CENTRES[0]);R.configure(m);K.write_obj(folder/(variant+'.obj'),m,'orion_pad');K.write_vmdl(folder/(variant+'.vmdl'),'models/maps/orion/mount-lamps-v1',variant,m)
 faces=S.read_obj(folder/(variant+'.obj'))[1];local=[]
 for mat,corners in faces:
  q=[]
  for p,uv,nrm in corners:
   a,b,c=map(float,p.split());q.append((f'{a+e:.3f} {b-z:.3f} {c-n:.3f}',uv,nrm))
  local.append((mat,tuple(q)))
 S.write_obj(folder/(variant+'.obj'),['mtllib '+variant+'.mtl\n','o '+variant+'\n'],local)
S.write_obj(folder/'pad_preview.obj',['mtllib pad_preview.mtl\n','o pad_preview\n'],result)
(folder/'pad_preview.mtl').write_bytes((ROOT/(base+'.mtl')).read_bytes())
text=(ROOT/(base+'.vmdl')).read_bytes().decode().replace('models/maps/orion/orion_pad.obj','models/maps/orion/mount-lamps-v1/pad_preview.obj');assert 'mount-lamps-v1/pad_preview.obj' in text
(folder/'pad_preview.vmdl').write_bytes(text.encode())
plan=dict(guards=guards,centres=G.CENTRES,removed=sum(removed.values()),added=len(added),preserved=len(public)-sum(removed.values()),files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'preview-plan.json').write_text(json.dumps(plan,indent=2));print({k:v for k,v in plan.items() if k not in ('guards','files')})
for file in ('native.py','import_preview.cs.txt','direct.py'):
 s=(ROOT/'Sources/Boxyard/pallet-stack-v1'/file).read_text().replace('Sources/Boxyard/pallet-stack-v1','Sources/Orion/mount-lamps-v1').replace('boxyard/pallet-stack-v1','orion/mount-lamps-v1');(HERE/file).write_text(s)
s=(ROOT/'Sources/Orion/yard-lamp-v1/capture.cs.txt').read_text().replace('output/orion/yard-lamp-v1','Sources/Orion/mount-lamps-v1/review').replace('models/maps/orion/yard-lamp-v1/','models/maps/orion/mount-lamps-v1/').replace('new Vector3(0,0,-12.2f)','new Vector3(0,0,-6.2f)').replace('W(18,-32,-8)','W(16,-23,12)').replace('W(0,0,-3)','W(0,0,-1)').replace('1000,1150','1000,1000').replace('FieldOfView=34','FieldOfView=28')
(HERE/'capture.cs.txt').write_text(s)
s=(ROOT/'Sources/Orion/yard-lamp-v1/context.cs.txt').read_text().replace('output/orion/yard-lamp-v1/context','Sources/Orion/mount-lamps-v1/review/context')
s=s.replace('scene.Deserialize(root);','''scene.Deserialize(root);
        foreach(var renderer in scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath=="models/maps/orion/orion_pad.vmdl"))renderer.Model=Model.Load("models/maps/orion/mount-lamps-v1/pad_preview.vmdl");''')
s=s.replace('new Vector3(215f,116f,74f)',f'new Vector3({e+30}f,{n-40}f,{z+20}f)').replace('new Vector3(181f,166f,95f)',f'new Vector3({e}f,{n}f,{z-12}f)').replace('Fov: 37f','Fov: 46f')
s=s.replace('new Vector3(120f,65f,72f)',f'new Vector3({e-85}f,{n-130}f,{z+65}f)').replace('new Vector3(181f,166f,50f)',f'new Vector3({e+40}f,{n+50}f,{z-35}f)')
(HERE/'context.cs.txt').write_text(s);p=OUT/'context';p.mkdir(exist_ok=True);(p/'config.json').write_text(json.dumps(dict(phase='preview',width=1600,height=1000,stream_frames=65,settle_frames=30)))
s=(ROOT/'Sources/Boxyard/pallet-stack-v1/compile.py').read_text().replace('boxyard/pallet-stack-v1','orion/mount-lamps-v1').replace("('before','stack','props_preview')","('before','lamp','pad_preview')");(HERE/'compile.py').write_text(s)
