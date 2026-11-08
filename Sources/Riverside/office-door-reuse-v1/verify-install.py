from pathlib import Path
from collections import Counter
import hashlib,json,sys
import numpy as np
ROOT=Path(sys.argv[1]).resolve();OUT=ROOT/'output/riverside/office-door-reuse-v1/installed'
plan=json.loads((OUT/'plan.json').read_text());before=json.loads((OUT/'before-install/riverside.scene').read_text());live=json.loads((OUT/'session-before.json').read_text());scene=json.loads((ROOT/'Assets/scenes/maps/Riverside/riverside.scene').read_text())
group=next(g for g in scene['GameObjects'] if g.get('Name')=='Office Entry Doors');assert len(group['Children'])==1
a=group['Children'][0];b=plan['group']['Children'][0]
def vec(v):return np.array([float(x) for x in v.split(',')])
for k in ('Position','Scale'):assert np.allclose(vec(a[k]),vec(b[k]),atol=1e-4,rtol=0)
qa,qb=vec(a['Rotation']),vec(b['Rotation']);assert abs(np.dot(qa,qb)/np.linalg.norm(qa)/np.linalg.norm(qb))>1-1e-10
assert len(a['Components'])==1 and a['Components'][0]['__type']=='Sandbox.ModelRenderer'
model=a['Components'][0]['Model'];model=model.get('Path') if isinstance(model,dict) else model;assert model=='models/props/riverside/trailer_door_v1/door.vmdl'
def normalize(v):
    if isinstance(v,dict):return {k:normalize(x) for k,x in v.items() if k!='__PrefabIdToInstanceId'}
    if isinstance(v,list):return [normalize(x) for x in v]
    return v
old_roots={g['__guid']:normalize(g) for g in live['GameObjects']};new_roots={g['__guid']:normalize(g) for g in scene['GameObjects'] if g.get('Name')!='Office Entry Doors'}
assert old_roots==new_roots,'Unrelated live objects changed during save'
assert {k:v for k,v in before.items() if k!='GameObjects'}=={k:v for k,v in scene.items() if k!='GameObjects'}
path=ROOT/plan['source'];assert hashlib.sha256(path.read_bytes()).hexdigest()==plan['after_sha256']
assert hashlib.sha256(path.with_suffix('.vmdl').read_bytes()).hexdigest()==plan['model_sha256']
old=Counter((OUT/'before-install/riverside_pad.obj').read_bytes().splitlines(keepends=True));new=Counter(path.read_bytes().splitlines(keepends=True));cut=old-new
assert not new-old and sum(cut.values())==16 and all(x.startswith(b'f ') for x in cut)
report=dict(saved_doors=1,old_panel_faces_removed=16,all_other_lowland_lines_preserved=True,all_existing_scene_objects_preserved=True,scene_properties_unchanged=True,complete_modeldoc_and_physics_unchanged=True,new_lights=0,new_colliders=0)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
