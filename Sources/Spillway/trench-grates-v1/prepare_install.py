from pathlib import Path
from collections import Counter
import json,sys,hashlib,shutil,time
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;OUT=ROOT/'output/spillway/trench-grates-v1';STAGE=OUT/'install-stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as P,spillway_map as R,riverdale_splice as S
import grate
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(rel,text):
 p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='')
base='Assets/models/maps/spillway/spillway_cargo';tool='Tools/spillway_map.py'
inputs=[tool,*[base+'.'+ext for ext in ('obj','mtl','vmdl')],'Assets/scenes/maps/spillway/spillway.scene']
inputs += [p.relative_to(ROOT).as_posix() for p in (ROOT/'Assets/models/maps/spillway').glob('*hulls*.obj')]
guards={rel:sha(ROOT/rel) for rel in inputs};baseline='before-'+str(time.time_ns())
for rel in inputs:
 p=OUT/baseline/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
old=K.Model();new=K.Model()
for e,n,w,h in grate.PLACEMENTS:
 P.quad(old,'rv_grating',(e,n,.35),(1,0,0),(0,1,0),w,h)
 grate.grate(new,(e,n,0),w,h)
R.configure(old);R.configure(new)
K.write_obj(OUT/'removed.obj',old,'spillway_cargo');removed=Counter(S.read_obj(OUT/'removed.obj')[1])
K.write_obj(OUT/'added.obj',new,'spillway_cargo');added=S.read_obj(OUT/'added.obj')[1]
header,original=S.read_obj(ROOT/(base+'.obj'))
assert sum(removed.values())==10 and not removed-Counter(original),'The five original grates differ'
result=list((Counter(original)-removed).elements())+added
p=STAGE/(base+'.obj');p.parent.mkdir(parents=True,exist_ok=True);S.write_obj(p,header,result)
text=(ROOT/(base+'.vmdl')).read_bytes().decode();eol='\r\n' if '\r\n' in text else '\n';anchor=next(l for l in text.splitlines() if 'from = ' in l)
remaps=eol.join(f'\t\t\t\t\t\t\t{{ from = "{key}.vmat" to = "{path}" }},' for key,path in grate.MATS.items())
put(base+'.vmdl',text.replace(anchor,remaps+eol+anchor,1))
put(base+'.mtl',(ROOT/(base+'.mtl')).read_bytes().decode()+''.join(f'\nnewmtl {k}\nKd 1 1 1\nd 1\n' for k in grate.MATS))
text=(ROOT/tool).read_text();needle='        P.quad(m,"rv_grating",(e,n,.35),(1,0,0),(0,1,0),w,h)'
assert text.count(needle)==1
text=text.replace(needle,'        from spillway_trench_grates import grate as draw_trench_grate\n        draw_trench_grate(m,(e,n,0),w,h)',1)
put(tool,text);put('Tools/spillway_trench_grates.py',(HERE/'grate.py').read_text())
plan=dict(baseline=baseline,guards=guards,files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},
 grates=5,removed_triangles=10,added_triangles=len(added),preserved_faces=len(original)-10)
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps({k:v for k,v in plan.items() if k not in ('guards','files')},indent=2))
script=(ROOT/'Sources/Riverside/searchlight-v1/install.cs.txt').read_text().replace('output/riverside/searchlight-v1','output/spillway/trench-grates-v1')
start=script.index('var allowed=');end=script.index('\nforeach',start)
script=script[:start]+'var allowed=new[]{'+','.join(json.dumps(p) for p in plan['files'])+'};'+script[end:]
script=script.replace('Tools/riverside_searchlight.py','Tools/spillway_trench_grates.py').replace('Searchlights=1','TrenchGrates=5')
(HERE/'install.cs.txt').write_text(script)
