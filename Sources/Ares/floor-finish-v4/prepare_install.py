"""Merge this approved-for-review floor into the pending constructed hall patch."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/floor-finish-v4';BASE=ROOT/'output/ares/constructed-interior-v3';STAGE=OUT/'install-stage'
old=json.loads((BASE/'install-plan.json').read_text());manifest=json.loads((OUT/'manifest.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in old['guards'].items():assert sha(ROOT/p)==h,'Published input changed: '+p
for p,h in old['files'].items():
    source=BASE/'install-stage'/p;assert sha(source)==h,'Pending base changed: '+p
    target=STAGE/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
def put(rel,text):
    p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='')
doc=(OUT/'stage/Assets/models/maps/ares/floor-finish-v4/ares_hall_trial.vmdl').read_text()
doc=doc.replace('models/maps/ares/floor-finish-v4/hall.obj','models/maps/ares/pressure-doors-v2/hall_base.obj',1)
put('Assets/models/maps/ares/ares_hall.vmdl',doc)
put('Assets/models/maps/ares/pressure-doors-v2/hall_base.obj',(OUT/'stage/Assets/models/maps/ares/floor-finish-v4/hall.obj').read_text().replace('mtllib hall.mtl','mtllib hall_base.mtl'))
put('Assets/models/maps/ares/pressure-doors-v2/hall_base.mtl',(OUT/'stage/Assets/models/maps/ares/floor-finish-v4/hall.mtl').read_text())
g=(STAGE/'Tools/ares_constructed.py').read_text()
g+='''
# Generated floor finish: apply one coordinated finish to hall plates and the
# previously dark gallery floors, at matching physical texture density.
MATERIALS[FLOOR]='materials/ares/floor-finish-v4/plate.vmat'
_constructed_config=config
def config(m):
    _constructed_config(m)
    if 'ar_floor' in m.polygons:
        m.material_overrides['ar_floor']='materials/ares/floor-finish-v4/grip.vmat'
        m.tile_overrides['ar_floor']=80.
    return m
'''
put('Tools/ares_constructed.py',g)
a=(STAGE/'Tools/ares_map.py').read_text()
needle='("materials/ares/constructed-v3/", "materials/ares/surface-finish-v2/")'
assert needle in a
a=a.replace(needle,'("materials/ares/constructed-v3/", "materials/ares/surface-finish-v2/", "materials/ares/floor-finish-v4/")')
put('Tools/ares_map.py',a)
for p in STAGE.glob('Tools/*.py'):compile(p.read_text(),str(p),'exec')
plan=dict(old)
plan.update(files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},
    approved=False,requires_active_scene='scenes/maps/ares/ares.scene',
    review=['gallery-after.png','ground-after.png','hero-after.png'],
    floor=dict(gallery_tile_inches=80,retiled_faces=manifest['floor_uv_faces'],physics_changed=False))
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2))
s=(ROOT/'Sources/Ares/constructed-interior-v3/install.cs.txt').read_text().replace('output/ares/constructed-interior-v3','output/ares/floor-finish-v4')
(ROOT/'Sources/Ares/floor-finish-v4/install.cs.txt').write_text(s)
print(json.dumps(dict(files=len(plan['files']),floor=plan['floor']),indent=2))
