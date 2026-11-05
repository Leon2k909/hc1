from pathlib import Path
from collections import Counter
import json,sys,hashlib,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'review';STAGE=OUT/'stage';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_splice as S,boxyard_map as R
import stack as G
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base='Assets/models/maps/boxyard/boxyard_props'
inputs=['Tools/boxyard_map.py','Assets/scenes/maps/Boxyard/boxyard.scene']+[base+'.'+e for e in ('obj','mtl','vmdl')]
inputs += [p.relative_to(ROOT).as_posix() for p in (ROOT/'Assets/models/maps/boxyard').glob('boxyard_props*hulls*.obj')]
inputs += [p.relative_to(ROOT).as_posix() for p in G.SOURCE.parent.glob('*') if p.is_file() and not p.name.endswith(('.meta','_c'))]
guards={k:sha(ROOT/k) for k in inputs}
for rel in inputs:
 p=OUT/'baseline'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
old=G.original(K.Model());new=G.build(K.Model());R.configure(old);R.configure(new)
K.write_obj(OUT/'removed.obj',old,'boxyard_props');removed=Counter(S.read_obj(OUT/'removed.obj')[1])
K.write_obj(OUT/'added.obj',new,'boxyard_props');added=S.read_obj(OUT/'added.obj')[1]
header,public=S.read_obj(ROOT/(base+'.obj'));assert not removed-Counter(public),'Original stack mismatch'
result=list((Counter(public)-removed).elements())+added
folder=STAGE/'Assets/models/maps/boxyard/pallet-stack-v1';folder.mkdir(parents=True,exist_ok=True)
for variant,m in [('before',old),('stack',new)]:
 K.write_obj(folder/(variant+'.obj'),m,'boxyard_props');K.write_vmdl(folder/(variant+'.vmdl'),'models/maps/boxyard/pallet-stack-v1',variant,m)
 faces=S.read_obj(folder/(variant+'.obj'))[1];local=[]
 for mat,corners in faces:
  q=[]
  for p,uv,n in corners:
   a,b,c=map(float,p.split());q.append((f'{a+G.CENTRE[0]:.3f} {b:.3f} {c-G.CENTRE[1]:.3f}',uv,n))
  local.append((mat,tuple(q)))
 S.write_obj(folder/(variant+'.obj'),['mtllib '+variant+'.mtl\n','o '+variant+'\n'],local)
S.write_obj(folder/'props_preview.obj',['mtllib props_preview.mtl\n','o props_preview\n'],result)
(folder/'props_preview.mtl').write_bytes((ROOT/(base+'.mtl')).read_bytes()+b'\nnewmtl bxps_wood\nKd 1 1 1\n')
text=(ROOT/(base+'.vmdl')).read_bytes().decode().replace('models/maps/boxyard/boxyard_props.obj','models/maps/boxyard/pallet-stack-v1/props_preview.obj')
eol='\r\n' if '\r\n' in text else '\n';anchor=next(l for l in text.splitlines() if 'from = ' in l)
text=text.replace(anchor,'\t\t\t\t\t\t\t{ from = "bxps_wood.vmat" to = "'+G.MATERIAL+'" },'+eol+anchor,1)
(folder/'props_preview.vmdl').write_bytes(text.encode())
plan=dict(guards=guards,removed=sum(removed.values()),added=len(added),preserved=len(public)-sum(removed.values()),files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'preview-plan.json').write_text(json.dumps(plan,indent=2));print({k:v for k,v in plan.items() if k not in ('guards','files')})
for file in ('native.py','import_preview.cs.txt'):
 s=(ROOT/'Sources/ReefHall/office-desk-v1'/file).read_text().replace('Sources/ReefHall/office-desk-v1','Sources/Boxyard/pallet-stack-v1').replace('reefhall/office-desk-v1','boxyard/pallet-stack-v1');(HERE/file).write_text(s)
s=(ROOT/'Sources/ReefHall/office-desk-v1/capture.cs.txt').read_text().replace('Sources/ReefHall/office-desk-v1','Sources/Boxyard/pallet-stack-v1').replace('reefhall/office-desk-v1','boxyard/pallet-stack-v1').replace('"before","desk"','"before","stack"').replace('W(95,-125,90)','W(60,-85,57)').replace('W(0,0,26)','W(0,0,8)').replace('FieldOfView=42','FieldOfView=38');(HERE/'capture.cs.txt').write_text(s)
s=(ROOT/'Sources/Orion/yard-lamp-v1/context.cs.txt').read_text().replace('output/orion/yard-lamp-v1/context','Sources/Boxyard/pallet-stack-v1/review/context').replace('Assets/scenes/maps/Orion/orion.scene','Assets/scenes/maps/Boxyard/boxyard.scene').replace('"Orion"','"Boxyard"')
s=s.replace('scene.Deserialize(root);','''scene.Deserialize(root);
        foreach(var renderer in scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath=="models/maps/boxyard/boxyard_props.vmdl"))renderer.Model=Model.Load("models/maps/boxyard/pallet-stack-v1/props_preview.vmdl");''')
s=s.replace('new Vector3(215f,116f,74f)','new Vector3(-545f,-720f,90f)').replace('new Vector3(181f,166f,95f)','new Vector3(-632f,-589f,12f)').replace('Fov: 37f','Fov: 48f')
s=s.replace('new Vector3(120f,65f,72f)','new Vector3(-405f,-730f,135f)').replace('new Vector3(181f,166f,50f)','new Vector3(-630f,-590f,30f)').replace('Fov: 75f','Fov: 75f');(HERE/'context.cs.txt').write_text(s)
p=OUT/'context';p.mkdir(exist_ok=True);(p/'config.json').write_text(json.dumps(dict(phase='preview',width=1600,height=1000,stream_frames=65,settle_frames=30)))
