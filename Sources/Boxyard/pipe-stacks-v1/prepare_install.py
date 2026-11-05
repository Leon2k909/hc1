from pathlib import Path
from collections import Counter
import json,sys,hashlib,shutil,time
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;OUT=ROOT/'output/boxyard/pipe-stacks-v1';STAGE=OUT/'install-stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,boxyard_map as B,riverdale_splice as S
import pipes
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(rel,text):
 p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='')
base='Assets/models/maps/boxyard/boxyard_props';tool='Tools/boxyard_map.py'
inputs=[tool,*[base+'.'+ext for ext in ('obj','mtl','vmdl')],'Assets/scenes/maps/Boxyard/boxyard.scene']
inputs += [p.relative_to(ROOT).as_posix() for p in (ROOT/'Assets/models/maps/boxyard').glob('*hulls*.obj')]
guards={rel:sha(ROOT/rel) for rel in inputs};baseline='before-'+str(time.time_ns())
for rel in inputs:
 p=OUT/baseline/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
old=K.Model();new=K.Model()
for e,n,heading in pipes.PLACEMENTS:B.pipes(old,e,n,heading);pipes.stack(new,e,n,heading)
B.configure(old);B.configure(new)
assert not new.boxes and not new.hulls
K.write_obj(OUT/'removed.obj',old,'boxyard_props');removed=Counter(S.read_obj(OUT/'removed.obj')[1])
K.write_obj(OUT/'added.obj',new,'boxyard_props');added=S.read_obj(OUT/'added.obj')[1]
header,original=S.read_obj(ROOT/(base+'.obj'))
assert not removed-Counter(original),'The original pipe stacks differ'
result=list((Counter(original)-removed).elements())+added
p=STAGE/(base+'.obj');p.parent.mkdir(parents=True,exist_ok=True);S.write_obj(p,header,result)
text=(ROOT/(base+'.vmdl')).read_bytes().decode();eol='\r\n' if '\r\n' in text else '\n';anchor=next(l for l in text.splitlines() if 'from = ' in l)
remaps=eol.join(f'\t\t\t\t\t\t\t{{ from = "{key}.vmat" to = "{path}" }},' for key,path in pipes.MATS.items())
put(base+'.vmdl',text.replace(anchor,remaps+eol+anchor,1))
put(base+'.mtl',(ROOT/(base+'.mtl')).read_bytes().decode()+''.join(f'\nnewmtl {k}\nKd 1 1 1\nd 1\n' for k in pipes.MATS))
text=(ROOT/tool).read_text();start=text.index('    for x in ( -55.0, 55.0 ):',text.index('def pipes('));end=text.index('    F.box( m, -84.0',start)
text=text[:start]+'''    from boxyard_pipe_stacks import stack as draw_pipe_stack
    draw_pipe_stack(m,e,n,heading)
    r = 4.3
'''+text[end:]
put(tool,text);put('Tools/boxyard_pipe_stacks.py',(HERE/'pipes.py').read_text())
plan=dict(baseline=baseline,guards=guards,files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},
 stacks=2,removed_triangles=sum(removed.values()),added_triangles=len(added),preserved_faces=len(original)-sum(removed.values()))
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps({k:v for k,v in plan.items() if k not in ('guards','files')},indent=2))
script=(ROOT/'Sources/Riverside/searchlight-v1/install.cs.txt').read_text().replace('output/riverside/searchlight-v1','output/boxyard/pipe-stacks-v1')
start=script.index('var allowed=');end=script.index('\nforeach',start)
script=script[:start]+'var allowed=new[]{'+','.join(json.dumps(p) for p in plan['files'])+'};'+script[end:]
script=script.replace('Tools/riverside_searchlight.py','Tools/boxyard_pipe_stacks.py').replace('Searchlights=1','PipeStacks=2')
(HERE/'install.cs.txt').write_text(script)
