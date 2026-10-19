from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
manifest = json.loads((OUT/'manifest.json').read_text())
native = json.loads((OUT/'native-geometry-verification.json').read_text())
assert len(native['grates'])==24 and all(x['Passed'] for x in native['grates'])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(ROOT/p)==h for p,h in manifest['staged_files'].items())
review = json.loads((OUT/'review/visual-review.json').read_text())
capture = json.loads((OUT/'review/capture.json').read_text())
assert review['accepted'] and len(review['views']) == 4
assert capture['scene'] == 'scenes/maps/lowtide/lowtide.scene' and not capture['HasUnsavedChanges']
floor_record = json.loads((OUT.parent/'grate-floor-support.json').read_text())
floor_hits = [json.loads(line) for line in floor_record['stdout'].splitlines() if line.strip()]
assert len(floor_hits) == 24 and all(hit['Hit'] and not hit['StartedSolid'] and abs(float(hit['EndPosition'].split(',')[2])) < .001 for hit in floor_hits)
restoration = json.loads((OUT.parent/'grate-review-restore.json').read_text())
restored_state = [json.loads(line) for line in restoration['stdout'].splitlines() if line.strip()][-1]
assert restored_state['IsPlaying'] and restored_state['ActiveScenePath'] == 'scenes/maps/spillway/spillway.scene'
assert restored_state['LastCompileSucceeded'] and restored_state['LastCompileErrors'] == 0
status = dict(
    revision=manifest['revision'], observed_utc=datetime.now(timezone.utc).isoformat(),
    project_root=str(ROOT), status='installed_native_visual_and_collision_review_complete',
    grates=24, native_geometry_checks_passed=24,
    new_source_triangles=manifest['delta_triangles']+sum(x['added_faces']-x['changed_faces'] for x in manifest['pavement'].values()),
    collision_changed=False, canonical_generator_integrated=True,
    installed_files=manifest['staged_files'],
    native_geometry_evidence=str((OUT/'native-geometry-verification.json').relative_to(ROOT)),
    source_geometry_evidence=str((OUT/'verification.json').relative_to(ROOT)),
    source_image='Sources/Lowtide/drainage/cast-iron-source.png',
    prompt='Sources/Lowtide/drainage/cast-iron-prompt.txt',
    image_generation='built-in image_gen',
    visual_review_complete=True, gameplay_performance_measured=False,
    visual_review_evidence=str((OUT/'review/visual-review.json').relative_to(ROOT)),
    reviewed_images={name:sha(OUT/'review'/name) for name in review['views']},
    native_floor_support_checks_passed=len(floor_hits),
    native_floor_support_evidence=str((OUT.parent/'grate-floor-support.json').relative_to(ROOT)),
    current_editor_state='Spillway opened and play started as explicitly requested; Veridant tab left open without edits by this pass and Lowtide camera restored',
    restoration_evidence=str((OUT.parent/'grate-review-restore.json').relative_to(ROOT)),
    excluded_screenshot='native-2026-10-18/grate-before.png captured Spillway after the user switched to play; not grate evidence',
    important='Historical finish/window/drainage OBJ stages precede the new grates and paving holes; recompose their scoped faces against current sources instead of replacing whole meshes.',
    overall_AAA_verified=False)
path=ROOT/'Sources/Lowtide/drainage/grate-status.json'
path.write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
checkout=ROOT/'Sources/Lowtide/construction/checkout-status.json'
data=json.loads(checkout.read_text())
data['latest_native_work']='Sources/Lowtide/drainage/grate-status.json'
data['user_work_mode']='native_checks_resumed'
data['historical_snapshot_note']='The four candidates and protected-file counts above describe the earlier offline snapshot. Grate geometry/materials were subsequently installed; consult latest_native_work before composing other mesh stages.'
checkout.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:status[k] for k in ('status','grates','native_geometry_checks_passed','new_source_triangles','visual_review_complete')},indent=2))
