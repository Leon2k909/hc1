"""Prepare the three tank replacements against the current public mesh, without a map rebuild."""
from pathlib import Path
from collections import Counter
import json,sys,hashlib,shutil,time
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/riverside/pole-transformer-v1';STAGE=OUT/'install-stage';STAGE.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as P,riverside_map as R,riverdale_splice as S
import transformer,layout
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(rel,text):
 p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='');return p
asset='Assets/models/maps/riverside/riverside_dressing.obj';doc='Assets/models/maps/riverside/riverside_dressing.vmdl';mtl='Assets/models/maps/riverside/riverside_dressing.mtl';tool='Tools/riverside_parts.py'
protected=[ROOT/tool,ROOT/asset,ROOT/doc,ROOT/mtl,ROOT/'Assets/scenes/maps/riverside/riverside.scene',*sorted((ROOT/'Assets/models/maps/riverside').glob('*hulls*.obj'))]
guards={p.relative_to(ROOT).as_posix():sha(p) for p in protected}
baseline='before-'+str(time.time_ns()) if '--rebase' in sys.argv else 'before'
for rel in (asset,doc,mtl,tool):
 b=OUT/baseline/rel;b.parent.mkdir(parents=True,exist_ok=True)
 if b.exists():assert sha(b)==sha(ROOT/rel),'Baseline changed: '+rel
 else:shutil.copy2(ROOT/rel,b)
old=K.Model();new=K.Model()
placements=layout.placements()
for spec in placements:
 c=spec['centre'];P.cylinder(old,c,9,c[2]-16,c[2]+16,'rs_steel',12,top='rs_steel',bottom='rs_steel')
 transformer.transformer(new,c,spec['facing'],spec['primary'])
R.configure(old);R.configure(new)
K.write_obj(OUT/'removed.obj',old,'riverside_dressing');removed=Counter(S.read_obj(OUT/'removed.obj')[1])
K.write_obj(OUT/'added.obj',new,'riverside_dressing');added=S.read_obj(OUT/'added.obj')[1]
header,original=S.read_obj(ROOT/asset)
assert sum(removed.values())==132
assert not removed-Counter(original),'The original three cans no longer match the installed model'
result=list((Counter(original)-removed).elements())+added
target=STAGE/asset;target.parent.mkdir(parents=True,exist_ok=True);S.write_obj(target,header,result)
assert Counter(original)-removed==Counter(result)-Counter(added)
assert not new.hulls and not new.boxes
text=(ROOT/doc).read_bytes().decode('utf-8');original_doc=text;eol='\r\n' if '\r\n' in text else '\n'
anchor=next(line for line in text.splitlines() if 'from = ' in line)
remaps=eol.join(f'\t\t\t\t\t\t\t{{ from = "{key}.vmat" to = "{value}" }},' for key,value in transformer.MATS.items())
text=text.replace(anchor,remaps+eol+anchor,1)
marker='_class = "PhysicsShapeList"';assert text[text.index(marker):]==original_doc[original_doc.index(marker):]
put(doc,text);put(mtl,(ROOT/mtl).read_bytes().decode('utf-8')+''.join(f'\nnewmtl {key}\nKd 1 1 1\nd 1\n' for key in transformer.MATS))
text=(ROOT/tool).read_text()
needle='        cylinder( m, c, 9, c[2] - 16, c[2] + 16, "rs_steel", 12, top="rs_steel", bottom="rs_steel" )'
assert text.count(needle)==1
text=text.replace(needle,'        from riverside_pole_transformer import transformer as draw_transformer\n        draw_transformer( m, c, f, taps[0] )',1)
put(tool,text);put('Tools/riverside_pole_transformer.py',(HERE/'transformer.py').read_text())
for p in (STAGE/'Tools').glob('*.py'):compile(p.read_text(),str(p),'exec')
plan=dict(baseline=baseline,guards=guards,files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},
          placements=[{k:np.asarray(v).tolist() for k,v in p.items()} for p in placements],original_triangles=len(original),
          removed_triangles=sum(removed.values()),added_triangles=len(added),final_triangles=len(result),preserved_faces=len(original)-sum(removed.values()),
          scene_unchanged=True,collision_unchanged=True,existing_wire_endpoints_preserved=True)
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps({k:v for k,v in plan.items() if k not in ('guards','files','placements')},indent=2))
