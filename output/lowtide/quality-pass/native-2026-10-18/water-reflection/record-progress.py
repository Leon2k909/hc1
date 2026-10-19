from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
REL=OUT.relative_to(ROOT).as_posix()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,data):p.write_text(json.dumps(data,indent=2)+'\n')

manifest=json.loads((OUT/'manifest.json').read_text())
canonical=json.loads((OUT/'canonical-verification.json').read_text())
assert all(sha(ROOT/p)==h for p,h in canonical['installed'].items())
compile=json.loads((OUT/'native-compile.json').read_text())
assert compile['errors']==0 and not compile['IsBuilding']
finished=(OUT/'production-readback.json').is_file() and (OUT/'production/verification.json').is_file() and (OUT/'review-retired.json').is_file()
if finished:
    production=json.loads((OUT/'production-readback.json').read_text())
    lifecycle=json.loads((OUT/'production/verification.json').read_text())
    retired=json.loads((OUT/'review-retired.json').read_text())
    assert production['Model']=='models/maps/lowtide/lowtide_water.vmdl'
    assert all(m['ShaderName']=='shaders/hc1_lowtide_water_filtered.shader' and not m['IsError'] for m in production['Materials'])
    assert all(c['ActiveReflectionViews']==c['Expected'] for c in lifecycle['checks'])
    assert lifecycle['TabRestored'] and not lifecycle['HasUnsavedChanges'] and lifecycle['Enabled']
    assert retired['Removed'] and retired['ScenePreserved'] and retired['PlayStatePreserved']
    for p in retired['Archived']:
        assert not (ROOT/p).exists() and (OUT/'retired-review'/p).is_file()
for phase,count in [('baseline',3),('comparison',6)]:
    capture=json.loads((OUT/phase/'capture.json').read_text())
    assert len(capture['records'])==count and capture['ModelRestored'] and capture['TabRestored']
    assert not capture['HasUnsavedChanges']
    assert all(r['ActiveReflectionViews']==1 and (OUT/phase/r['name']).is_file() for r in capture['records'])
acceptance=dict(static_native_comparison_reviewed=True,images_reviewed=9,
    views=['canal axis','bank beside barge','reverse toward harbour'],
    findings=['Filtered reflected architecture is softer at distance and grazing angles.',
              'The moving-wave pattern, shallow transparency and bank edge remain visible.',
              'No error material, missing reflection or inversion appeared in these captures.'],
    limitations=['Wave time differs between sequential stills; these are not a temporal-stability test.',
                 'Production material readback, camera lifecycle checks and controlled performance are pending.'],
    filter_strength=.08,material_roughness=.22,overall_AAA_verified=False)
if finished:
    acceptance.update(images_reviewed=12,fresh_production_images_reviewed=3,
        production_readback_verified=True,editor_camera_lifecycle_checks_passed=6,
        limitations=['Sequential stills are not a temporal-stability test.',
                     'The performance sample failed its camera-angle guard and is not accepted as a Lowtide benchmark.',
                     'Controlled gameplay cost and moving-camera/multiple-view checks remain open.'])
write(OUT/'static-review.json',acceptance)
status_path=ROOT/'Sources/Lowtide/water/filter-status.json'
historical=OUT/'historical-filter-status.json'
if not historical.exists():shutil.copyfile(status_path,historical)
status=dict(date='2026-10-18',status='installed_after_native_static_review_runtime_verification_pending',
    project_root=str(ROOT),user_work_mode='native_checks_resumed',production_changed=True,
    native_accepted=False,static_native_comparison_reviewed=True,canonical_generator_changed=True,
    generator='Tools/lowtide_water_filter.py',canonical_generator='Tools/lowtide_water.py',
    shader_extension='Sources/Lowtide/water/reflection-filter.hlsl',
    installed=canonical['installed'],generators=canonical['generators'],
    scope=dict(max_mips=7,roughness_filter_scale=.08,base_roughness=.22,extra_water_texture_lookups=0,
               max_downsample_passes=6,additional_color_bytes_at_960x540=1380960,
               delta_triangles=0,new_material_slots=0,geometry_collision_and_scene_unchanged=True),
    evidence=dict(directory=REL,review=REL+'/static-review.json',native_compile=REL+'/native-compile.json',
                  unused_review_readback=REL+'/review-readback.json',production_import=REL+'/production-import.json',
                  canonical_reproduction=REL+'/canonical-verification.json'),
    native_validation=dict(capture_hotload_errors=0,review_material_compiled=True,
        reviewed_images=9,active_reflection_views_in_all_captures=1,
        production_compiled_file_exists=(ROOT/'Assets/materials/lowtide/lt_water.vmat_c').is_file(),
        production_compile_request_timed_out=True,production_loaded_material_readback=False,
        lifecycle_verified=False,temporal_stability_verified=False,gameplay_performance_measured=False),
    editor_state=dict(restored_play_scene='scenes/maps/ares/ares.scene',
        restoration='Native play_start confirmed Ares started after the brief review interruption.',
        later_state='User reports still loading or frozen; native editor/instance requests time out.',
        log='Repeated game-cache search-path failures and ToolsStallMonitor entries during Ares loading.',
        process_left_running=True),
    remaining=['After the editor responds, inspect the loaded production water material before retrying a timed-out compile.',
        'Run verify-production.cs, then a brief stopped-play verify-lifecycle.cs and review its fresh production captures.',
        'Measure controlled Lowtide gameplay/GPU performance and moving-camera appearance.',
        'Archive/remove the two unused review assets only after successful production readback and captures.'],
    historical_status=REL+'/historical-filter-status.json',overall_AAA_verified=False,
    observed_utc=datetime.now(timezone.utc).isoformat())
if finished:
    status.update(status='installed_native_visual_and_editor_lifecycle_verified',native_accepted=True)
    status['native_validation'].update(reviewed_images=12,production_loaded_material_readback=True,
        lifecycle_verified=True,lifecycle_scope='Six single-perspective editor checks: visible, outside bounds, below plane, return, disable and reenable.',
        performance_sample_rejected=True,performance_rejection='Camera orientation changed during the fixed-view sample; no Lowtide timing claim.')
    status['evidence'].update(production_readback=REL+'/production-readback.json',
        production_captures=REL+'/production/verification.json',review_cleanup=REL+'/review-retired.json',
        rejected_performance_sample=REL+'/performance-unaccepted.json')
    status['editor_state'].update(later_state='The editor recovered; production readback and all six lifecycle checks passed. Ares play was started again and the connection remained responsive.',
                                 process_left_running=True)
    status['remaining']=['Measure controlled Lowtide gameplay/GPU performance with verified camera context.',
                         'Review moving-camera temporal appearance and multiple-view behavior.']
    status['temporary_review_assets_archived']=len(retired['Archived'])
write(status_path,status)
checkout_path=ROOT/'Sources/Lowtide/construction/checkout-status.json'
checkout=json.loads(checkout_path.read_text())
checkout.update(status='grates_construction_paving_water_installed_performance_pending',
                observed_utc=status['observed_utc'],latest_native_work='Sources/Lowtide/water/filter-status.json')
water=checkout['candidates']['water-filter-gentle']
water.update(installed=True,native_accepted=finished,static_native_comparison_reviewed=True,
             current_installed_status='Sources/Lowtide/water/filter-status.json',historical_manifest_superseded=True)
checkout['remaining'][0]='Measure water gameplay cost and moving-camera temporal behavior.' if finished else 'Complete production water readback, camera lifecycle, temporal and controlled performance checks after the editor recovers.'
checkout['remaining'][2]='Review the revalidated warehouse floor/concrete candidates natively; revalidate foliage integration.'
checkout['historical_snapshot_note']='Candidate/protected-file counts describe the earlier offline snapshot. Grates, construction, paving and water are installed. See each current status for its native checks and performance limits. Sacks remain staged; historical full meshes must be recomposed against current sources.'
checkout['current_warehouse_floor_stage']='output/lowtide/quality-pass/native-2026-10-18/warehouse-floor-current/manifest.json'
if 'Sources/Lowtide/water/filter-status.json' not in checkout['native_work']:
    checkout['native_work'].append('Sources/Lowtide/water/filter-status.json')
write(checkout_path,checkout)
for rel in ['Sources/Lowtide/floor/floor-status.json','Sources/Lowtide/concrete/wear-status.json']:
    path=ROOT/rel;data=json.loads(path.read_text())
    data['latest_checkout_revalidation']=checkout['current_warehouse_floor_stage']
    data['current_support_geometry_validated']=True
    data['user_work_mode']='native_checks_resumed_editor_temporarily_unresponsive'
    data['historical_note']='Original offline preview evidence remains applicable to the unchanged materials. The current manifest verifies all 286 floor collision footprints and twelve mezzanine triangles; no floor assets are installed yet.'
    write(path,data)
print(json.dumps(dict(water_installed=True,native_static_images_reviewed=12 if finished else 9,capture_errors=0,
                     production_readback_pending=not finished,warehouse_stage_files=20,overall_AAA_verified=False),indent=2))
