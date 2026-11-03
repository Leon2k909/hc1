"""Install only the reviewed floor onto the current public hall, preserving other art."""
from pathlib import Path
from collections import Counter
import hashlib,json,sys,ast,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/ares/floor-live-v4';STAGE=OUT/'stage';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,ares_map as A,ares_interior as I,riverdale_splice as S
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(rel,text):
    p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='');return p
paths=['Assets/models/maps/ares/pressure-doors-v2/hall_base.obj','Assets/models/maps/ares/ares_hall.vmdl','Tools/ares_interior.py','Tools/ares_map.py','Assets/scenes/maps/Ares/ares.scene']
guards={}
for rel in paths:
    p=ROOT/rel;backup=OUT/'before'/rel;backup.parent.mkdir(parents=True,exist_ok=True)
    if backup.exists():assert sha(backup)==sha(p),'Input changed: '+rel
    else:shutil.copy2(p,backup)
    guards[rel]=sha(p)
helper='Tools/ares_floor_finish.py'
assert not (ROOT/helper).exists(),'New helper already exists; inspect before replacing'
geometry=(ROOT/'Sources/Ares/constructed-interior-v3/geometry.py').read_text();tree=ast.parse(geometry)
floor=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='floor')
source='''"""Generated Ares floor plates. Render geometry only; floor collision stays at z0."""
import numpy as np
import map_kit as K
import riverdale_parts as P
X=np.array((1.,0.,0.));Y=np.array((0.,1.,0.));Z=np.array((0.,0.,1.))
FLOOR='ar_in_floor';DARK='ar_in_dark'
def box(m,c,size,paint,b):P.bevel_box(m,c,(X,Y,Z),size,paint,b)
'''+ast.get_source_segment(geometry,floor)+'\n'
put(helper,source)
ns={};exec(compile(source,helper,'exec'),ns)
old=K.Model();I.floor(old);A.configure(old);I.configure(old)
K.write_obj(OUT/'removed.obj',old,'ares_hall');remove=Counter(S.read_obj(OUT/'removed.obj')[1])
new=K.Model();ns['floor'](new);A.configure(new);I.configure(new)
assert not new.boxes and not new.hulls
K.write_obj(OUT/'added.obj',new,'ares_hall');added=S.read_obj(OUT/'added.obj')[1]
header,original=S.read_obj(ROOT/paths[0]);have=Counter(original)
assert not remove-have,'Original floor does not match current public geometry'
retained=list((have-remove).elements());result=[];retiled=0;offset=K.uv_offset('ares_hall')
for paint,corners in retained:
    if paint=='ar_floor':
        corners=tuple((p,' '.join(f'{(float(v)-offset[i])*192/80+offset[i]:.6f}' for i,v in enumerate(uv.split())),n) for p,uv,n in corners)
        retiled+=1
    result.append((paint,corners))
result+=added
assert len(old.boxes)==len(new.boxes)==0 and not old.hulls and not new.hulls
target=STAGE/paths[0];target.parent.mkdir(parents=True,exist_ok=True);S.write_obj(target,header,result)
doc=(ROOT/paths[1]).read_text();original_doc=doc
assert 'materials/ares/interior-v1/floor.vmat' in doc and 'materials/ares/ar_floor.vmat' in doc
doc=doc.replace('materials/ares/interior-v1/floor.vmat','materials/ares/floor-finish-v4/plate.vmat').replace('materials/ares/ar_floor.vmat','materials/ares/floor-finish-v4/grip.vmat')
marker='_class = "PhysicsShapeList"';assert doc[doc.index(marker):]==original_doc[original_doc.index(marker):]
put(paths[1],doc)
i=(ROOT/'Tools/ares_interior.py').read_text()
i=i.replace('\ndef configure(m):',"\nMATERIALS[FLOOR]='materials/ares/floor-finish-v4/plate.vmat'\nMATERIALS['ar_floor']='materials/ares/floor-finish-v4/grip.vmat'\n\ndef configure(m):",1)
i=i.replace('m.tile_overrides[paint]=96. if paint in (PANEL,FLOOR) else 48.',"m.tile_overrides[paint]=80. if paint in (FLOOR,'ar_floor') else 96. if paint==PANEL else 48.")
begin=i.index('def floor(m):');end=i.index('\ndef append_hall(m):',begin)
i=i[:begin]+'''def floor(m):
    from ares_floor_finish import floor as draw_floor
    return draw_floor(m)

'''+i[end:]
put('Tools/ares_interior.py',i)
a=(ROOT/'Tools/ares_map.py').read_text()
a=a.replace('for paint in list( model.polygons ):','for paint in list( model.polygons ):\n        if model.material_overrides.get(paint, "").startswith("materials/ares/floor-finish-v4/"):\n            continue',1)
put('Tools/ares_map.py',a)
for p in STAGE.glob('Tools/*.py'):compile(p.read_text(),str(p),'exec')
plan=dict(guards=guards,new_files=[helper],files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},
    floor_only=True,scene_unchanged=True,collision_unchanged=True,original_triangles=len(original),removed_floor_triangles=sum(remove.values()),added_floor_triangles=len(added),retiled_existing_floor_triangles=retiled,
    final_triangles=len(result),preserved_other_faces=len(original)-sum(remove.values())-retiled,
    material_dependencies=['materials/ares/floor-finish-v4/plate.vmat','materials/ares/floor-finish-v4/grip.vmat'])
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps({k:v for k,v in plan.items() if k not in ('guards','files','new_files')},indent=2))
