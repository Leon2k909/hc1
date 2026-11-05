"""Reuse the approved stocked cabinet for the three close-range shop fridges; preview only."""
from pathlib import Path
import sys,json,hashlib,re,collections,ast
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverside_parts as P,riverside_map as R,riverside_drinks_fridge as F
OUT=ROOT/'output/riverside/interior-fridges-v1';STAGE=OUT/'stage';RES='models/props/riverside/interior_fridges_v1';MODEL=STAGE/'Assets'/RES;MODEL.mkdir(parents=True,exist_ok=True)
approved=F.model();local=P.place(approved,-np.array(F.CENTER),0)
count=K.write_model(MODEL,RES,'fridge',local);assert count==34152
old_local=K.Model();P.fridge(old_local,(0,0),(0,-1),0);old_local.boxes.clear();old_local.hulls.clear();R.configure(old_local);K.write_model(MODEL,RES,'legacy_fridge',old_local)
positions=[(R.STORE[1]-6-16,R.STORE[2]+120+k*34,R.STORE_FLOOR) for k in range(3)]
old=K.Model()
for e,n,z in positions:P.fridge(old,(e,n),(-1,0),z)
R.configure(old);K.write_obj(OUT/'legacy_absolute.obj',old,'old_interior_fridges')
tree=ast.parse((ROOT/'Sources/Riverside/still-here-board-v1/prepare_install.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='records');env={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'records','exec'),env);records=env['records']
_,fs=records(OUT/'legacy_absolute.obj');want=collections.Counter(k for _,k in fs);vmdl=ROOT/'Assets/models/maps/riverside/riverside_store.vmdl';vt=vmdl.read_text();source=None
for ref in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vt):
 p=ROOT/'Assets'/ref
 if not p.exists():continue
 ls,fs=records(p)
 if not want-collections.Counter(k for _,k in fs):source=p;break
assert source,'Interior fridge faces differ from authored originals'
cut=set()
for i,k in fs:
 if want[k]:cut.add(i);want[k]-=1
assert len(cut)==42 and not +want
(MODEL/'store_without_fridges.obj').write_text(''.join(l for i,l in enumerate(ls) if i not in cut).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib store_without_fridges.mtl'))
(MODEL/'store_without_fridges.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'store_without_fridges.vmdl').write_text(vt.replace(source.relative_to(ROOT/'Assets').as_posix(),RES+'/store_without_fridges.obj'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected=[source,vmdl,ROOT/'Assets/scenes/maps/Riverside/riverside.scene',ROOT/'Tools/riverside_drinks_fridge.py',ROOT/'Assets/models/maps/riverside/drinks-fridge-v1/drinks_fridge.obj']
external={('Assets/'+v):sha(ROOT/'Assets'/v) for v in local.material_overrides.values()}
m=dict(preview_only=True,reuses_approved='Riverside porch drinks fridge v1',triangles=count,instances=3,positions=[K.to_world(p).tolist() for p in positions],yaw=-90,removed_old_triangles=42,resource=RES+'/fridge.vmdl',background=RES+'/store_without_fridges.vmdl',protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},external_files=external,files={p.relative_to(STAGE).as_posix():sha(p) for p in MODEL.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps({k:v for k,v in m.items() if k not in ('files','external_files')},indent=2))
template=(ROOT/'Sources/Riverside/tower-roof-v1/import.cs.txt').read_text().replace('tower-roof-v1','interior-fridges-v1').replace('tower_roof_v1','interior_fridges_v1')
(Path(__file__).parent/'import.cs.txt').write_text(template)
