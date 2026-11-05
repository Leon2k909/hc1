from pathlib import Path
from collections import Counter
import hashlib,json,sys,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/spillway/service-cabinet-v1';STAGE=OUT/'stage';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as P,riverdale_splice as splice,spillway_map as S
import cabinet,paint
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(rel,text):
 p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='');return p
asset='Assets/models/maps/spillway/spillway_cargo.obj'
doc='Assets/models/maps/spillway/spillway_cargo.vmdl'
mtl='Assets/models/maps/spillway/spillway_cargo.mtl'
tool='Tools/spillway_map.py'
paths=[asset,doc,mtl,tool,'Assets/scenes/maps/spillway/spillway.scene',*['Assets/models/maps/spillway/'+p.name for p in (ROOT/'Assets/models/maps/spillway').glob('*hulls*.obj')]]
guards={rel:sha(ROOT/rel) for rel in paths}
for rel in paths:
 b=OUT/'before'/rel;b.parent.mkdir(parents=True,exist_ok=True)
 if b.exists():assert sha(b)==sha(ROOT/rel),'Baseline changed: '+rel
 else:shutil.copy2(ROOT/rel,b)

# Counter matching binds the comparison to the actual two published boxes.
old=K.Model()
for e in (-325,-280):P.box(old,e-18,e+18,332,358,0,79,'rv_steel')
S.configure(old);K.write_obj(OUT/'removed.obj',old,'spillway_cargo')
removed=Counter(splice.read_obj(OUT/'removed.obj')[1])
header,original=splice.read_obj(ROOT/asset)
assert not removed-Counter(original),'Expected old cabinets are not in the public cargo mesh'
assert sum(removed.values())==24
matroot=STAGE/'Assets/materials/spillway/service-cabinet-v1';paint.build(matroot)
modelroot=STAGE/'Assets/models/maps/spillway/service-cabinet-v1';modelroot.mkdir(parents=True,exist_ok=True)
new=cabinet.model()
assert not new.boxes and not new.hulls
new_triangles=K.write_obj(modelroot/'cabinet.obj',new,'spillway_cargo')
K.write_vmdl(modelroot/'cabinet.vmdl','models/maps/spillway/service-cabinet-v1','cabinet',new)
# Exact published original is translated to the same origin for the neutral comparison.
before=[]
for material,corners in list(removed.elements())[:12]:
 before.append((material,tuple((' '.join(f'{v:.3f}' for v in (float(p.split()[0])-325,float(p.split()[1]),float(p.split()[2])-345)),uv,n) for p,uv,n in corners)))
splice.write_obj(modelroot/'before.obj',['mtllib before.mtl\n','o before\n'],before)
(modelroot/'before.mtl').write_text('newmtl rv_steel\nKd 1 1 1\nd 1\n')
oldlocal=K.Model();P.box(oldlocal,-18,18,-13,13,0,79,'rv_steel');S.configure(oldlocal)
K.write_vmdl(modelroot/'before.vmdl','models/maps/spillway/service-cabinet-v1','before',oldlocal)
floor=K.Model();P.box(floor,-450,450,-450,450,-2,-.05,'sw_concrete');S.configure(floor)
K.write_obj(modelroot/'review_floor.obj',floor,'spillway_cargo');K.write_vmdl(modelroot/'review_floor.vmdl','models/maps/spillway/service-cabinet-v1','review_floor',floor)

placed=K.Model()
for e in (-325,-280):cabinet.cabinet(placed,(e,345,0))
K.write_obj(OUT/'added.obj',placed,'spillway_cargo')
added=splice.read_obj(OUT/'added.obj')[1]
result=list((Counter(original)-removed).elements())+added
target=STAGE/asset;target.parent.mkdir(parents=True,exist_ok=True);splice.write_obj(target,header,result)
assert Counter(original)-removed==Counter(result)-Counter(added)
old_doc=(ROOT/doc).read_bytes().decode('utf-8');new_doc=old_doc
eol='\r\n' if '\r\n' in old_doc else '\n'
anchor=next(line for line in old_doc.splitlines() if 'from = ' in line)
remaps=eol.join(f'\t\t\t\t\t\t\t{{ from = "{key}.vmat" to = "{value}" }},' for key,value in cabinet.MATS.items())
new_doc=new_doc.replace(anchor,remaps+eol+anchor,1)
physics='_class = "PhysicsShapeList"'
assert new_doc[new_doc.index(physics):]==old_doc[old_doc.index(physics):]
put(doc,new_doc)
put(mtl,(ROOT/mtl).read_bytes().decode('utf-8')+''.join(f'\nnewmtl {key}\nKd 1 1 1\nd 1\n' for key in cabinet.MATS))
text=(ROOT/tool).read_text()
needle='    for e in (-325,-280):\n        box(m,e-18,e+18,332,358,0,79,"rv_steel",METAL)'
assert needle in text
text=text.replace(needle,'''    from spillway_service_cabinet import cabinet as service_cabinet
    for e in (-325,-280):
        service_cabinet(m,(e,345,0))
        box(m,e-18,e+18,332,358,0,79,{"default":None},METAL)''',1)
put(tool,text);put('Tools/spillway_service_cabinet.py',(HERE/'cabinet.py').read_text())
for p in (STAGE/'Tools').glob('*.py'):compile(p.read_text(),str(p),'exec')
points=[p for faces in new.polygons.values() for ps,n in faces for p in ps]
import numpy as np
bounds=np.array(points);low=bounds.min(axis=0);high=bounds.max(axis=0)
assert np.all(low>=np.array((-18,-13,0))-.01) and np.all(high<=np.array((18,13,79))+.01),(low,high)
files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()}
plan=dict(guards=guards,files=files,original_triangles=len(original),removed_triangles=24,added_triangles=len(added),
          new_cabinet_triangles=new_triangles,final_triangles=len(result),preserved_other_faces=len(original)-24,
          bounds=[low.tolist(),high.tolist()],scene_unchanged=True,collision_unchanged=True)
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps({k:v for k,v in plan.items() if k not in ('guards','files')},indent=2))
