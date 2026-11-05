from pathlib import Path
from collections import Counter
import hashlib,json,sys
import numpy as np
ROOT=Path(sys.argv[1]).resolve();OUT=ROOT/'output/asset-improvement-20261030/riverside-street-lamp/installed'
plan=json.loads((OUT/'plan.json').read_text());scene=json.loads((ROOT/'Assets/scenes/maps/Riverside/riverside.scene').read_text());before=json.loads((OUT/'before-install/riverside.scene').read_text())
group=next(g for g in scene['GameObjects'] if g.get('Name')=='Streetlight Heads');assert len(group['Children'])==4
def vec(v):return np.array([float(x) for x in v.split(',')] if isinstance(v,str) else v)
for a,b in zip(group['Children'],plan['group']['Children']):
    for key in ('Position','Scale'):assert np.allclose(vec(a[key]),vec(b[key]),atol=1e-5),(a['Name'],key)
    qa,qb=vec(a['Rotation']),vec(b['Rotation']);assert abs(np.dot(qa,qb)/np.linalg.norm(qa)/np.linalg.norm(qb))>1-1e-10
    assert len(a['Components'])==1 and a['Components'][0]['__type']=='Sandbox.ModelRenderer'
    model=a['Components'][0]['Model'];assert (model.get('Path') if isinstance(model,dict) else model)==b['Components'][0]['Model']
path=ROOT/plan['source'];assert hashlib.sha256(path.read_bytes()).hexdigest()==plan['after_sha256']
assert hashlib.sha256(path.with_suffix('.vmdl').read_bytes()).hexdigest()==plan['model_sha256']
old=Counter((OUT/'before-install/riverside_dressing.obj').read_bytes().splitlines(keepends=True));new=Counter(path.read_bytes().splitlines(keepends=True));cut=old-new
assert not new-old and sum(cut.values())==56 and all(l.startswith(b'f ') for l in cut)
def lights(data):
    result=[]
    def walk(g):
        for c in g.get('Components',[]):
            if c['__type'] in ('Sandbox.PointLight','Sandbox.SpotLight'):result.append((g['__guid'],g.get('Position'),g.get('Rotation'),c))
        for child in g.get('Children',[]):walk(child)
    for g in data['GameObjects']:walk(g)
    return result
assert lights(scene)==lights(before),'Existing lights changed'
assert len(next(g for g in scene['GameObjects'] if g.get('Name')=='Porch Lights')['Children'])==26
report=dict(saved_streetlights=4,old_faces_removed=56,all_unrelated_mesh_lines_preserved=True,complete_modeldoc_and_physics_unchanged=True,existing_lights_unchanged=True,porch_lights_retained=26)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
