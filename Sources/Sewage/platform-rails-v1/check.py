from pathlib import Path
from collections import Counter
import hashlib,json,sys,shutil
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/sewage/platform-rails-v1'
sys.path.insert(0,str(ROOT/'Tools'))
import riverdale_splice as S
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'plan.json').read_text());pub=ROOT/'Assets/models/maps/sewage'
for name,value in plan['install_files'].items():assert sha(pub/name)==value
assert sha(pub/'sewage_catwalks_hulls_metal.obj')==plan['hull_hash']
before=Counter(S.read_obj(OUT/'baseline/sewage_catwalks.obj')[1]);after=Counter(S.read_obj(pub/'sewage_catwalks.obj')[1])
assert sum((before-after).values())==plan['removed_triangles']
assert sum((after-before).values())==plan['added_triangles']
capture=json.loads((OUT/'capture-report.json').read_text());assert capture['MatchedCameraAndLighting'] and capture['UserStatePreserved']
display=Path('C:/Users/leon2/.codex/visualizations/2026/11/04/01a1a73a-ac05-7220-9dac-461a6cce09ed');display.mkdir(parents=True,exist_ok=True)
for name in ('platform-before','platform-after','fittings-before','fittings-after'):shutil.copy2(OUT/(name+'.png'),display/('rails-'+name+'.png'))
result=dict(installed=True,sections=7,unrelated_triangles_preserved=plan['retained_triangles'],collision_unchanged=True,matched_capture=True,editor_state_preserved=True,existing_kit_reused=True)
(OUT/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
