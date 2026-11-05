from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/sewage/rail-texture-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'plan.json').read_text());pub=ROOT/'Assets/models/maps/sewage/sewage_catwalks.vmdl'
for name,value in plan['files'].items():assert sha(ROOT/name)==value,name
assert sha(pub.with_suffix('.obj'))==plan['obj_hash']
assert sha(pub.with_suffix('.mtl'))==plan['mtl_hash']
assert sha(pub.with_name('sewage_catwalks_hulls_metal.obj'))==plan['hull_hash']
before=(OUT/'baseline/sewage_catwalks.vmdl').read_text();after=pub.read_text()
assert after.replace('materials/sewage/rail-texture-v1/enamel.vmat','materials/sewage/yellow.vmat')==before
capture=json.loads((OUT/'capture-report.json').read_text());assert capture['MatchedCameraAndLighting']
installed=json.loads((OUT/'installed.json').read_text());assert installed['UserStatePreserved']
display=Path('C:/Users/leon2/.codex/visualizations/2026/11/04/01a1a73a-ac05-7220-9dac-461a6cce09ed');display.mkdir(parents=True,exist_ok=True)
for name in ('platform-before','platform-after','fittings-before','fittings-after'):shutil.copy2(OUT/(name+'.png'),display/('enamel-'+name+'.png'))
result=dict(installed=True,only_material_slot='ww_platform_rail',geometry_unchanged=True,collision_unchanged=True,matched_capture=True,installation_editor_state_preserved=True,capture_user_state_unchanged=capture['UserStatePreserved'],capture_note='User changed from Riverside edit to Riverdale play independently during isolated capture; no restoration attempted.',generation='built-in imagegen')
(OUT/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
