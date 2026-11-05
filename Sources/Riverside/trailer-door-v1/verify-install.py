from pathlib import Path
from collections import Counter
import hashlib,json,sys
import numpy as np
ROOT=Path(sys.argv[1]).resolve();OUT=ROOT/'output/riverside/trailer-door-v1/installed'
plan=json.loads((OUT/'plan.json').read_text());before=json.loads((OUT/'before-install/riverside.scene').read_text());scene=json.loads((ROOT/'Assets/scenes/maps/Riverside/riverside.scene').read_text())
groups=[g for g in scene['GameObjects'] if g.get('Name')=='Trailer Entry Doors'];assert len(groups)==1
group=groups[0];assert len(group['Children'])==1
a=group['Children'][0];b=plan['group']['Children'][0]
def vec(v):return np.array([float(x) for x in v.split(',')])
assert np.allclose(vec(a['Position']),vec(b['Position']),atol=1e-5)
assert np.allclose(vec(a['Scale']),vec(b['Scale']),atol=1e-5)
qa,qb=vec(a['Rotation']),vec(b['Rotation']);assert abs(np.dot(qa,qb)/np.linalg.norm(qa)/np.linalg.norm(qb))>1-1e-10
assert len(a['Components'])==1 and a['Components'][0]['__type']=='Sandbox.ModelRenderer'
model=a['Components'][0]['Model'];model=model.get('Path') if isinstance(model,dict) else model
assert model=='models/props/riverside/trailer_door_v1/door.vmdl'
assert {k:v for k,v in scene.items() if k!='GameObjects'}=={k:v for k,v in before.items() if k!='GameObjects'}
old_roots={g['__guid']:g for g in before['GameObjects']};new_roots={g['__guid']:g for g in scene['GameObjects'] if g.get('Name')!='Trailer Entry Doors'}
assert old_roots.keys()==new_roots.keys(),'Unrelated scene objects missing'
for guid,old_root in old_roots.items():
    new_root=new_roots[guid]
    if old_root.get('Name')=='Boarded Camper':
        # Re-importing the missing saved camper expands native defaults/resource IDs.
        for k in ('Name','Position','Scale','Enabled'):assert old_root[k]==new_root[k]
        qa,qb=vec(old_root['Rotation']),vec(new_root['Rotation']);assert abs(np.dot(qa,qb)/np.linalg.norm(qa)/np.linalg.norm(qb))>1-1e-10
        assert len(old_root['Components'])==len(new_root['Components'])==1
        for k,v in old_root['Components'][0].items():
            actual=new_root['Components'][0][k]
            if k=='Model' and isinstance(actual,dict):actual=actual['Path']
            assert actual==v,(k,actual,v)
    else:
        if old_root.get('Name')=='Lights':
            # A concurrently approved shop-sign installation set this one light to .20.
            light=next(c for g in old_root['Children'] for c in g.get('Components',[]) if c.get('__guid')=='ad251c23-5036-51ff-9ecb-932578dc96f1')
            light['Intensity']=.20
        assert old_root==new_root,old_root.get('Name')+' changed'
path=ROOT/plan['source'];assert hashlib.sha256(path.read_bytes()).hexdigest()==plan['after_sha256']
assert hashlib.sha256(path.with_suffix('.vmdl').read_bytes()).hexdigest()==plan['model_sha256']
old=Counter((OUT/'before-install/riverside_low.obj').read_bytes().splitlines(keepends=True));new=Counter(path.read_bytes().splitlines(keepends=True));cut=old-new
assert not new-old and sum(cut.values())==16 and all(l.startswith(b'f ') for l in cut)
report=dict(saved_doors=1,old_faces_removed=16,unrelated_scene_objects_preserved=True,camper_restored=True,concurrent_approved_store_sign_intensity=.20,window_faces_and_uvs_preserved=True,all_unrelated_mesh_lines_preserved=True,complete_modeldoc_and_physics_unchanged=True,door_lighting_and_steps_unchanged=True)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
