from pathlib import Path
from collections import Counter
import json,sys,hashlib,shutil,time
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;OUT=ROOT/'output/orion/yard-lamp-v1';STAGE=OUT/'install-stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,orion_map as R,riverdale_splice as S
import lamp
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(rel,text):
 p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='')
base='Assets/models/maps/orion/orion_props';tool='Tools/orion_map.py'
inputs=[tool,*[base+'.'+ext for ext in ('obj','mtl','vmdl')],'Assets/scenes/maps/Orion/orion.scene']
inputs += [p.relative_to(ROOT).as_posix() for p in (ROOT/'Assets/models/maps/orion').glob('*hulls*.obj')]
guards={rel:sha(ROOT/rel) for rel in inputs};baseline='before-'+str(time.time_ns())
for rel in inputs:
 p=OUT/baseline/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
old=lamp.original(K.Model());new=lamp.head(K.Model());R.configure(old);R.configure(new)
assert not new.boxes and not new.hulls
K.write_obj(OUT/'removed.obj',old,'orion_props');removed=Counter(S.read_obj(OUT/'removed.obj')[1])
K.write_obj(OUT/'added.obj',new,'orion_props');added=S.read_obj(OUT/'added.obj')[1]
header,original=S.read_obj(ROOT/(base+'.obj'))
assert sum(removed.values())==14 and not removed-Counter(original),'Original head differs'
result=list((Counter(original)-removed).elements())+added
p=STAGE/(base+'.obj');p.parent.mkdir(parents=True,exist_ok=True);S.write_obj(p,header,result)
text=(ROOT/(base+'.vmdl')).read_bytes().decode();eol='\r\n' if '\r\n' in text else '\n';anchor=next(l for l in text.splitlines() if 'from = ' in l)
remaps=eol.join(f'\t\t\t\t\t\t\t{{ from = "{key}.vmat" to = "{path}" }},' for key,path in lamp.MATS.items())
put(base+'.vmdl',text.replace(anchor,remaps+eol+anchor,1));put(base+'.mtl',(ROOT/(base+'.mtl')).read_bytes().decode()+''.join(f'\nnewmtl {k}\nKd 1 1 1\nd 1\n' for k in lamp.MATS))
text=(ROOT/tool).read_text();needle='''    box( m, 176, 186, 160, 172, 92, 100, "oa_dark" )
    card( m, "oa_lamp_warm", [ v( 177, 161, 91.9 ), v( 185, 161, 91.9 ), v( 185, 171, 91.9 ), v( 177, 171, 91.9 ) ], -UP )'''
assert text.count(needle)==1
text=text.replace(needle,'    from orion_yard_lamp import head as draw_yard_lamp\n    draw_yard_lamp(m)',1)
put(tool,text);put('Tools/orion_yard_lamp.py',(HERE/'lamp.py').read_text())
plan=dict(baseline=baseline,guards=guards,files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},
 lamps=1,removed_triangles=14,added_triangles=len(added),preserved_faces=len(original)-14)
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps({k:v for k,v in plan.items() if k not in ('guards','files')},indent=2))
script=(ROOT/'Sources/Riverside/searchlight-v1/install.cs.txt').read_text().replace('output/riverside/searchlight-v1','output/orion/yard-lamp-v1')
start=script.index('var allowed=');end=script.index('\nforeach',start)
script=script[:start]+'var allowed=new[]{'+','.join(json.dumps(p) for p in plan['files'])+'};'+script[end:]
script=script.replace('Tools/riverside_searchlight.py','Tools/orion_yard_lamp.py').replace('Searchlights=1','YardLamps=1')
(HERE/'install.cs.txt').write_text(script)
