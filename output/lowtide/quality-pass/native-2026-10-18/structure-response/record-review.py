"""Record accepted lighting persistence and the rejected structure surface trial."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[4]
FLOOR=OUT.parent/'warehouse-floor-current'
def read(p): return json.loads(p.read_text())
def write(p,data): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(data,indent=2)+'\n')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

manifest=read(OUT/'manifest.json')
assert all(sha(ROOT/p)==h for p,h in manifest['protected'].items())
assert all(not (ROOT/'Assets'/p).exists() for p in manifest['assets'])
review=read(OUT/'review-lit/capture.json')
assert review['OverridesRestored'] and review['TabRestored'] and not review['HasUnsavedChanges']
assert len(review['captures'])==9
reload=read(OUT/'lighting-reload/readback.json')
assert not reload['HasUnsavedChanges'] and len(reload['Volumes'])==2
assert all(not v['Error'] and v['Enabled'] and v['Active'] and '-v4/' in v['Path'] for v in reload['Volumes'])
dest=FLOOR/'lighting-persistence'
dest.mkdir(exist_ok=True)
copied=[]
for row in review['captures']:
    if row['variant']!='before': continue
    source=OUT/'review-lit'/row['file']
    target=dest/row['file'].replace('-before','')
    shutil.copyfile(source,target)
    copied.append(dict(path=target.relative_to(ROOT).as_posix(),sha256=sha(target),position=row['position'],angles=row['angles']))
result=dict(status='saved_v4_lighting_verified_after_scene_reload',
    scene_sha256=sha(ROOT/'Assets/scenes/maps/Lowtide/lowtide.scene'),
    reviewed_loaded_views=copied,loaded_volumes=reload['Volumes'],
    stale_editor_state='After swapping baked texture paths the existing volumes needed reactivation. The saved scene then reloaded with both v4 volumes active and contributing, without reactivation.',
    diagnostic_evidence=OUT.relative_to(ROOT).as_posix()+'/lighting-diagnostic/readback.json',
    reload_evidence=OUT.relative_to(ROOT).as_posix()+'/lighting-reload/readback.json',
    retired_generated_files_remain_unneeded=True,scene_source_changed_during_diagnostic=False,
    gameplay_performance_verified=False)
write(dest/'verification.json',result)
for p in [FLOOR/'lighting/verification.json',FLOOR/'verification.json',ROOT/'Sources/Lowtide/floor/floor-status.json',ROOT/'Sources/Lowtide/concrete/wear-status.json',ROOT/'Sources/Lowtide/lighting/bake-provenance.json']:
    data=read(p)
    data['persistence_reload_verified']=True
    data['persistence_evidence']=(dest/'verification.json').relative_to(ROOT).as_posix()
    write(p,data)
trial=dict(date='2026-10-18',observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='reviewed_not_accepted_sources_retired',production_changed=False,
    reviewed_lit_comparisons=9,evidence=OUT.relative_to(ROOT).as_posix()+'/review-lit/capture.json',
    invalid_early_comparison='review/ was captured with stale DDGI and must not be used to judge the material.',
    findings=['The current standard shader and lighter tint recover timber detail.',
        'The reused railhead wood scan contains repeated plank seams, inappropriate for solid structural beams.',
        'Cast iron columns remain too dark; a brighter generic tint alone is not accepted.'],
    next_steps=['Use individual long-grain beam faces with correct UV orientation and no plank seams.',
        'Inspect cast iron material response and surface normals, then review at close range and in daylight.',
        'Rebake warehouse indirect light after accepted structural material changes.'],
    retained_candidates=OUT.relative_to(ROOT).as_posix()+'/stage',
    cleanup=OUT.relative_to(ROOT).as_posix()+'/retired.json',
    lighting_persistence=result['status'],overall_AAA_verified=False)
write(ROOT/'Sources/Lowtide/structure/response-status.json',trial)
write(OUT/'verification.json',trial)
print(json.dumps(dict(lightingPersistence=True,loadedViews=len(copied),structureInstalled=False)))
