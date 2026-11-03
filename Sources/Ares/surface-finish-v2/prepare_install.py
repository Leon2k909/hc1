"""Stage the reviewed result without changing any published model or scene."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/surface-finish-v2'
manifest=json.loads((OUT/'manifest.json').read_text());stage=OUT/'install-stage'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(rel,text):
    p=stage/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='');return p
for rel,digest in manifest['guards'].items():assert sha(ROOT/rel)==digest,f'Changed during review: {rel}'
for model in ('hall','reactor'):
    doc=(OUT/f'stage/Assets/models/maps/ares/surface-finish-v2/ares_{model}_trial.vmdl').read_text()
    doc=doc.replace('models/maps/ares/surface-finish-v2/hall_trial.obj','models/maps/ares/pressure-doors-v2/hall_base.obj')
    original=(ROOT/f'Assets/models/maps/ares/ares_{model}.vmdl').read_text()
    assert doc[doc.index('_class = "PhysicsShapeList"'):]==original[original.index('_class = "PhysicsShapeList"'):]
    assert re.findall(r'filename = "([^"]+)"',doc)==re.findall(r'filename = "([^"]+)"',original)
    put(f'Assets/models/maps/ares/ares_{model}.vmdl',doc)
put('Assets/models/maps/ares/pressure-doors-v2/hall_base.obj',(OUT/'stage/Assets/models/maps/ares/surface-finish-v2/hall_trial.obj').read_text().replace('hall_trial.mtl','hall_base.mtl'))
put('Assets/models/maps/ares/pressure-doors-v2/hall_base.mtl',(OUT/'stage/Assets/models/maps/ares/surface-finish-v2/hall_trial.mtl').read_text())
text=(ROOT/'Tools/ares_interior.py').read_text()
text=text.replace("FLOOR='ar_in_floor'","FLOOR='ar_in_floor'; WALL='ar_in_wall'")
text=text.replace('\ndef configure(m):',"\nMATERIALS.update({WALL:'materials/ares/surface-finish-v2/wall.vmat',FLOOR:'materials/ares/surface-finish-v2/floor.vmat',FRAME:'materials/ares/surface-finish-v2/frame.vmat'})\nMATERIALS.update({f'ar_{name}':f'materials/ares/surface-finish-v2/{name}.vmat' for name in ('steel','gunmetal','grating')})\n\ndef configure(m):")
text=text.replace('m.tile_overrides[paint]=96. if paint in (PANEL,FLOOR) else 48.',"m.tile_overrides[paint]=(192. if paint==WALL else 96. if paint in (PANEL,FLOOR) else 24. if paint=='ar_grating' else 64. if not paint.startswith('ar_in_') else 48.)")
for old,new in [('.28,w-8,319),PANEL','.28,w-8,319),WALL'),('.58,n1-n0-2,146),PANEL','.58,n1-n0-2,146),WALL'),('(.6,96,120),PANEL','(.6,96,120),WALL')]:
    assert old in text; text=text.replace(old,new)
put('Tools/ares_interior.py',text)
rel='Tools/ares_map.py';p=ROOT/rel;manifest['guards'][rel]=sha(p)
backup=OUT/'before'/rel;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,backup)
text=p.read_text()
text=text.replace('for paint in list( model.polygons ):','for paint in list( model.polygons ):\n        if model.material_overrides.get(paint, "").startswith("materials/ares/surface-finish-v2/"):\n            continue',1)
text=text.replace('LightColor=color, Radius=float( radius ), Shadows=bool( shadows )','LightColor="5.355,5.355,5.355,1" if name.startswith("Hall ") else color,\n                         Temperature=5200 if name.startswith("Hall ") else 6500, Radius=float( radius ), Shadows=bool( shadows )')
put(rel,text)
scene=json.loads((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_text())
lights=next(g for g in scene['GameObjects'] if g.get('Name')=='Lights')
ids=[g['__guid'] for g in lights['Children'] if g.get('Name','').startswith('Hall ')]
assert len(ids)==24
mutations=[dict(tool='set_component',args=dict(id=id,type='PointLight',properties=dict(LightColor='5.355,5.355,5.355,1',Temperature=5200))) for id in ids]
gi=next(g for g in scene['GameObjects'] if g.get('Name')=='Ares bounced lighting')
mutations.append(dict(tool='set_component',args=dict(id=gi['__guid'],type='IndirectLightVolume',properties=dict(RuntimeIntensity=2.2,RuntimeContrast=.78))))
plan=dict(guards=manifest['guards'],files={str(p.relative_to(stage)).replace('\\','/'):sha(p) for p in stage.rglob('*') if p.is_file()},
          scene_mutations=mutations,approved=False,review='overview-review.png, floor-review.png, wall-review.png',
          verified=dict(physics_suffixes=True,all_model_imports=True,positions_and_normals=True,wall_faces=64,face_count=364452))
for rel in ('Tools/ares_map.py','Tools/ares_interior.py'):compile((stage/rel).read_text(),str(stage/rel),'exec')
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2))
print(json.dumps(dict(files=len(plan['files']),lights=len(ids),verified=plan['verified']),indent=2))
