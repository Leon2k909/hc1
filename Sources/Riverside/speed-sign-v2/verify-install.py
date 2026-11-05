from pathlib import Path
from collections import Counter
import hashlib,json,sys
import numpy as np
ROOT=Path(sys.argv[1]).resolve()
OUT=ROOT/'output/asset-improvement-20261030/riverside-speed-sign/installed'
plan=json.loads((OUT/'plan.json').read_text())
scene=json.loads((ROOT/'Assets/scenes/maps/Riverside/riverside.scene').read_text())
group=next(g for g in scene['GameObjects'] if g.get('Name')=='Speed-Limit Signs')
assert len(group['Children'])==1
actual=group['Children'][0];expected=plan['group']['Children'][0]
def vec(v):return [float(x) for x in v.split(',')] if isinstance(v,str) else v
for key in ('Position','Rotation','Scale'):assert np.allclose(vec(actual[key]),vec(expected[key]),atol=1e-5),key
assert len(actual['Components'])==1
model=actual['Components'][0]['Model']
assert (model.get('Path') if isinstance(model,dict) else model)==expected['Components'][0]['Model']
path=ROOT/plan['source']
assert hashlib.sha256(path.read_bytes()).hexdigest()==plan['after_sha256']
assert hashlib.sha256(path.with_suffix('.vmdl').read_bytes()).hexdigest()==plan['model_sha256']
old=Counter((OUT/'before-install/riverside_pad.obj').read_bytes().splitlines(keepends=True));new=Counter(path.read_bytes().splitlines(keepends=True))
assert not new-old
assert sum((old-new).values())==16 and all(l.startswith(b'f ') for l in old-new)
assert len(next(g for g in scene['GameObjects'] if g.get('Name')=='Sandbags')['Children'])==54
report=dict(saved_signs=1,removed_old_faces=16,all_unrelated_mesh_lines_preserved=True,original_collision_model_unchanged=True,sandbags=54)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
