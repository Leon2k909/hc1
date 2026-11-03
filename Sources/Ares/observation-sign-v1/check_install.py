from pathlib import Path
import json,hashlib,sys
from native import call,script,OUT,ROOT
HERE=Path(__file__).parent
result=call('asset_compile',dict(path='models/maps/ares/ares_dressing.vmdl',full=True))
print(json.dumps(result),flush=True);assert result['Success']
config=json.loads((OUT/'capture-config.json').read_text());config['variants']=['installed']
(OUT/'capture-config.json').write_text(json.dumps(config,indent=2))
capture=script(HERE/'baseline.cs.txt');print(json.dumps(capture),flush=True)
assert capture['UserStatePreserved'] and not capture['ErrorModels']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text());guard=json.loads((OUT/'install-source-guard.json').read_text())
changed=[p for p,h in guard.items() if sha(ROOT/p)!=h]
assert changed==[plan['target']],changed
assert sha(ROOT/plan['target'])==plan['after_sha256']
old=(OUT/'install-before/ares_dressing.vmdl').read_text();new=(ROOT/plan['target']).read_text()
assert old[old.index('_class = "PhysicsShapeList"'):]==new[new.index('_class = "PhysicsShapeList"'):]
sys.path.insert(0,str(ROOT/'Tools'))
import ares_observation_sign as S
import map_kit as K
m=S.model();generated=OUT/'generator-sign.obj';K.write_obj(generated,m,'observation_sign')
assert generated.read_text().splitlines()[3:]==(ROOT/'Assets/models/maps/ares/observation-sign-v1/observation_sign.obj').read_text().splitlines()[3:]
status=call('editor_status');assert status['LastCompileSucceeded'] and not status['LastCompileErrors']
report=dict(installed=True,approval='User approved installation 2026-11-03',changed_original_assets=changed,physics_unchanged=True,scene_unchanged=True,generator_matches_approved_mesh=True,capture=capture,editor_status=status)
(OUT/'installed.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(installed=True,physics_unchanged=True,generator_matches_approved_mesh=True)))
