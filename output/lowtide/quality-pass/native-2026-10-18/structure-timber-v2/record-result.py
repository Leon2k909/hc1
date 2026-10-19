import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[5]
HERE=Path(__file__).resolve().parent
REL=HERE.relative_to(ROOT).as_posix()
sys.path.insert(0,str(ROOT/'Tools'))
import lowtide_structure as S

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
plan=read(HERE/'promotion-plan.json')
assert all(sha(ROOT/'Assets'/p)==h for p,h in plan['resources'].items())
assert all(sha(ROOT/'Assets'/row['path'])==row['after'] for row in plan['models'])
changed={'Assets/'+row['path'] for row in plan['models']}|{'Assets/scenes/maps/Lowtide/lowtide.scene','Sources/Lowtide/lighting/warehouse-lighting.json'}
assert all(sha(ROOT/p)==h for p,h in plan['protected'].items() if p not in changed)
assert all(sha(ROOT/p)==h for p,h in plan['paintDependencies'].items())
reproduction=HERE/'reproduction';assert not reproduction.exists()
S.write_materials(reproduction)
assert all(sha(reproduction/p)==h for p,h in plan['resources'].items())
reload=read(HERE/'production-reloaded/verification.json')
assert not reload['HasUnsavedChanges'] and reload['TabRestored']
assert len(reload['Volumes'])==2 and all(v['Active'] and v['Enabled'] and v['Error'] is False and '-v5/' in v['Path'] for v in reload['Volumes'])
assert all(len(x['Slots'])==2 and x['Count']==23 and all(s['Override'] is None and not s['Error'] for s in x['Slots']) for x in reload['bindings'])
for name in reload['Captures']:assert (HERE/'production-reloaded'/name).stat().st_size>10000
lighting=read(HERE/'lighting/verification.json')
assert sha(ROOT/'Assets/scenes/maps/Lowtide/lowtide.scene')==lighting['scene_sha256']
lighting.update(status='native_v5_bake_saved_and_fresh_load_reviewed',fresh_load_verified=True,reviewed_captures=6,visual_evidence=REL+'/production-reloaded/verification.json')
write(HERE/'lighting/verification.json',lighting)
provenance=ROOT/'Sources/Lowtide/lighting/bake-provenance.json'
data=read(provenance);data.update(status=lighting['status'],reviewedViewportCaptures=6,freshLoadVerified=True)
write(provenance,data)
result=dict(status='installed_native_reviewed_and_reload_verified',observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    project_root=str(ROOT),production_changed=True,assets=plan['resources'],models=plan['models'],
    generated_image=dict(source='Sources/Lowtide/structure/beam-timber-source.png',sha256=sha(S.SOURCE/'beam-timber-source.png'),
        tool='built-in image_gen',prompt='Sources/Lowtide/structure/beam-timber-prompt.txt',size=[1254,1254],generated_pixels_unchanged=True),
    numerical_surface_data=dict(physical_patch_metres=[.6,2.4],fibre_depth_metres=.0012,roughness_range=[.66,.9]),
    selected_iron='Weathered painted cast iron; marine paint scan reused unchanged',
    rejected_iron='Uniform casting/oxidation texture read too brown and stone-like in daylight',
    normal_audit=read(HERE/'normal-audit.json'),reviewed_comparison_captures=18,reviewed_production_captures=6,reviewed_fresh_load_captures=6,
    new_geometry=0,new_material_slots=0,collision_unchanged=True,canonical_resources_byte_exact=12,
    native_production=REL+'/production/verification.json',native_reloaded=REL+'/production-reloaded/verification.json',
    lighting=REL+'/lighting/verification.json',cleanup=[REL+'/retired-trial/cleanup.json',REL+'/lighting/cleanup.json'],
    restored_editor_tab='scenes/maps/orion/orion.scene',restored_runtime_map='scenes/maps/lowtide/lowtide.scene',
    remaining=['Broader warehouse lighting and cargo quality','Foliage and whole-map visual audit','Controlled gameplay performance, LOD switching and moving-camera temporal checks'],
    performance_verified=False,overall_AAA_verified=False)
write(HERE/'verification.json',result)
write(S.SOURCE/'material-status.json',result)
old=read(S.SOURCE/'response-status.json');old['superseded_by']='Sources/Lowtide/structure/material-status.json';write(S.SOURCE/'response-status.json',old)
for relative in ['Sources/Lowtide/floor/floor-status.json','Sources/Lowtide/concrete/wear-status.json']:
    p=ROOT/relative;x=read(p);x['later_structure_and_lighting_update']='Sources/Lowtide/structure/material-status.json';write(p,x)
print(json.dumps({k:result[k] for k in ['status','canonical_resources_byte_exact','reviewed_comparison_captures','reviewed_production_captures','reviewed_fresh_load_captures','new_geometry','new_material_slots','collision_unchanged','performance_verified','overall_AAA_verified']},indent=2))
