from pathlib import Path
from collections import Counter
import hashlib,json,sys
import numpy as np
ROOT=Path(sys.argv[1]).resolve();OUT=ROOT/'output/asset-improvement-20261030/riverside-pole-insulator/installed'
plan=json.loads((OUT/'plan.json').read_text());scene=json.loads((ROOT/'Assets/scenes/maps/Riverside/riverside.scene').read_text());before=json.loads((OUT/'before-install/riverside.scene').read_text())
group=next(g for g in scene['GameObjects'] if g.get('Name')=='Pole Insulators');assert len(group['Children'])==48
other_scene={**scene,'GameObjects':[g for g in scene['GameObjects'] if g.get('Name')!='Pole Insulators']}
assert other_scene==before,'Unrelated saved scene data changed'
def vec(v):return np.array([float(x) for x in v.split(',')] if isinstance(v,str) else v)
wired=0
for a,b,e in zip(group['Children'],plan['group']['Children'],plan['placements']):
    for key in ('Position','Scale'):assert np.allclose(vec(a[key]),vec(b[key]),atol=1e-5),(a['Name'],key)
    qa,qb=vec(a['Rotation']),vec(b['Rotation']);assert abs(np.dot(qa,qb)/np.linalg.norm(qa)/np.linalg.norm(qb))>1-1e-10
    assert np.allclose(vec(a['Position'])+np.array((0,0,5)),e['wire_contact'],atol=1e-5)
    assert len(a['Components'])==1 and a['Components'][0]['__type']=='Sandbox.ModelRenderer'
    model=a['Components'][0]['Model'];model=model.get('Path') if isinstance(model,dict) else model
    assert model==b['Components'][0]['Model'];wired+=model.endswith('/pole_insulator.vmdl')
assert wired==36
path=ROOT/plan['source'];assert hashlib.sha256(path.read_bytes()).hexdigest()==plan['after_sha256']
assert hashlib.sha256(path.with_suffix('.vmdl').read_bytes()).hexdigest()==plan['model_sha256']
old=Counter((OUT/'before-install/riverside_dressing.obj').read_bytes().splitlines(keepends=True));new=Counter(path.read_bytes().splitlines(keepends=True));cut=old-new
assert not new-old and sum(cut.values())==768 and all(l.startswith(b'f ') for l in cut)
def lights(data):
    result=[]
    def walk(g):
        for c in g.get('Components',[]):
            if c['__type'] in ('Sandbox.PointLight','Sandbox.SpotLight'):result.append((g['__guid'],g.get('Position'),g.get('Rotation'),c))
        for child in g.get('Children',[]):walk(child)
    for g in data['GameObjects']:walk(g)
    return result
assert lights(scene)==lights(before),'Existing lights changed'
for name,count in (('Porch Lights',26),('Streetlight Heads',4),('Sandbags',54)):
    assert len(next(g for g in scene['GameObjects'] if g.get('Name')==name)['Children'])==count
report=dict(saved_insulators=48,wired=36,bare=12,old_faces_removed=768,all_unrelated_scene_data_preserved=True,all_unrelated_mesh_lines_preserved=True,all_wire_contacts_unchanged=True,complete_modeldoc_and_physics_unchanged=True,existing_lights_unchanged=True)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
