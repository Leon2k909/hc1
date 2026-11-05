from pathlib import Path
from collections import Counter
import json,sys,hashlib,shutil,time
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;OUT=ROOT/'output/sewage/crane-blocks-v1';STAGE=OUT/'install-stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,sewage_map as R,riverdale_splice as S
import crane
R.PAINTS.update(steel=96,yellow=64)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(rel,text):
 p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='')
base='Assets/models/maps/sewage/sewage_details';tool='Tools/sewage_map.py'
inputs=[tool,*[base+'.'+ext for ext in ('obj','mtl','vmdl')],'Assets/scenes/maps/sewage/sewage.scene']
inputs += [p.relative_to(ROOT).as_posix() for p in (ROOT/'Assets/models/maps/sewage').glob('*hulls*.obj')]
guards={rel:sha(ROOT/rel) for rel in inputs};baseline='before-'+str(time.time_ns())
for rel in inputs:
 p=OUT/baseline/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
old=R.model();new=K.Model()
for e,n,z in crane.PLACEMENTS:crane.original(old,e,n,z);crane.block(new,(e,n,z))
assert not new.boxes and not new.hulls
K.write_obj(OUT/'removed.obj',old,'sewage_details');removed=Counter(S.read_obj(OUT/'removed.obj')[1])
K.write_obj(OUT/'added.obj',new,'sewage_details');added=S.read_obj(OUT/'added.obj')[1]
header,original=S.read_obj(ROOT/(base+'.obj'))
assert not removed-Counter(original),'Original hoist blocks differ'
result=list((Counter(original)-removed).elements())+added
p=STAGE/(base+'.obj');p.parent.mkdir(parents=True,exist_ok=True);S.write_obj(p,header,result)
text=(ROOT/(base+'.vmdl')).read_bytes().decode();eol='\r\n' if '\r\n' in text else '\n';anchor=next(l for l in text.splitlines() if 'from = ' in l)
remaps=eol.join(f'\t\t\t\t\t\t\t{{ from = "{key}.vmat" to = "{path}" }},' for key,path in crane.MATS.items())
put(base+'.vmdl',text.replace(anchor,remaps+eol+anchor,1))
put(base+'.mtl',(ROOT/(base+'.mtl')).read_bytes().decode()+''.join(f'\nnewmtl {k}\nKd 1 1 1\nd 1\n' for k in crane.MATS))
text=(ROOT/tool).read_text();start=text.index('        detail.box((e-23,n-20,z),(e+23,n+20,z+84)');end=text.index('    # Wall stencils',start)
text=text[:start]+'''        from sewage_crane_blocks import block as draw_crane_block
        draw_crane_block(detail,(e,n,z))
'''+text[end:]
put(tool,text);put('Tools/sewage_crane_blocks.py',(HERE/'crane.py').read_text())
plan=dict(baseline=baseline,guards=guards,files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},
 blocks=2,removed_triangles=sum(removed.values()),added_triangles=len(added),preserved_faces=len(original)-sum(removed.values()))
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps({k:v for k,v in plan.items() if k not in ('guards','files')},indent=2))
script=(ROOT/'Sources/Riverside/searchlight-v1/install.cs.txt').read_text().replace('output/riverside/searchlight-v1','output/sewage/crane-blocks-v1')
start=script.index('var allowed=');end=script.index('\nforeach',start)
script=script[:start]+'var allowed=new[]{'+','.join(json.dumps(p) for p in plan['files'])+'};'+script[end:]
script=script.replace('Tools/riverside_searchlight.py','Tools/sewage_crane_blocks.py').replace('Searchlights=1','CraneBlocks=2')
(HERE/'install.cs.txt').write_text(script)
