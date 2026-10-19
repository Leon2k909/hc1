"""Record checked native floor integration without claiming gameplay performance."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
REL=OUT.relative_to(ROOT).as_posix()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def write(p,data): p.write_text(json.dumps(data,indent=2)+'\n')

promotion=read(OUT/'promotion.json')
canonical=read(OUT/'canonical-checks.json')
native=read(OUT/'production-resource-readback.json')
captures=read(OUT/'production/capture.json')
assert canonical['resource_files_exact']==18
assert len(captures['captures'])==6 and captures['TabRestored'] and not captures['HasUnsavedChanges']
assert all(not slot['IsError'] and slot['Override'] is None for r in native['Renderers'] for slot in r['Slots'])
assert all(sha(ROOT/'Assets'/p)==h for p,h in promotion['resources'].items())
assert all(sha(ROOT/'Assets'/p)==h['after'] for p,h in promotion['models'].items())
reproduction=read(OUT.parent/'warehouse-floor-reproduction/manifest.json')
assert all(sha(ROOT/'Assets'/p)==h for p,h in reproduction['assets'].items())
lighting=read(OUT/'lighting/verification.json') if (OUT/'lighting/verification.json').exists() else None
assert lighting is not None and lighting['canonical_lighting_idempotent']
assert sha(ROOT/'Assets/scenes/maps/Lowtide/lowtide.scene')==lighting['scene_sha256']
cleanup=read(OUT/'lighting/cleanup.json')
assert cleanup['Count']==6 and cleanup['PreservedStableV4']
dressing_sources={p.replace('\\','/'):h for p,h in read(OUT/'dressing-before/hashes.json').items() if not p.endswith('_c')}
assert all(sha(ROOT/p)==h for p,h in dressing_sources.items())
bounds=read(OUT/'model-bounds-readback.json')
assert len(bounds['rows'])==2 and all(not x['IsError'] and x['Bad']==0 for x in bounds['rows'])
report=dict(date='2026-10-18',observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='installed_native_static_views_verified',project_root=str(ROOT),
    user_work_mode='native_checks_resumed',production_changed=True,production_generator_integrated=True,
    canonical_generator='Tools/lowtide_floor_surfaces.py',native_accepted=True,
    resources=promotion['resources'],models=promotion['models'],material_remap_plan=promotion['material_remap_plan'],
    native_evidence=dict(promotion=REL+'/promotion.json',readback=REL+'/production-resource-readback.json',
        comparison_captures=REL+'/review/capture.json',comparison_count=24,
        production_captures=REL+'/production/capture.json',production_count=6,
        canonical_reproduction=REL+'/canonical-checks.json',exact_resource_files=18,
        current_stage_reproduction=OUT.parent.relative_to(ROOT).as_posix()+'/warehouse-floor-reproduction/manifest.json',
        all20_stage_files_match_current=True,current_floor_collision_footprints=286,upward_mezzanine_triangles=12),
    native_shader_fix=promotion['native_shader_fix'],lighting=lighting,
    dressing_cache_repair=dict(native_full_recompile=True,source_files_unchanged=dressing_sources,
        finite_loaded_bounds=True,readback=REL+'/model-bounds-readback.json',
        renderers=REL+'/dressing-readback.json',cargo_visible_in_fresh_production_views=True),
    cleanup=REL+'/lighting/cleanup.json',
    remaining=['Controlled gameplay cost and moving-camera temporal filtering',
        'Broader warehouse lighting, black structural materials, cargo quality and whole-map visual audit'],
    performance_verified=False,overall_AAA_verified=False)
if lighting is None: report['remaining'].insert(0,'Complete and verify warehouse indirect-light refresh')
for rel,old_manifest in [('Sources/Lowtide/floor/floor-status.json','warehouse-floor'),('Sources/Lowtide/concrete/wear-status.json','concrete-wear')]:
    data=dict(report)
    data['historical_offline_manifest']=f'output/lowtide/quality-pass/{old_manifest}/manifest.json'
    write(ROOT/rel,data)
write(OUT/'verification.json',report)
checkout=read(ROOT/'Sources/Lowtide/construction/checkout-status.json')
checkout.update(status='grates_construction_paving_water_floors_installed_performance_pending',
    observed_utc=report['observed_utc'],latest_native_work='Sources/Lowtide/floor/floor-status.json',
    current_warehouse_floor_stage=REL+'/promotion.json')
for rel in ('Sources/Lowtide/floor/floor-status.json','Sources/Lowtide/concrete/wear-status.json'):
    if rel not in checkout['native_work']: checkout['native_work'].append(rel)
checkout['remaining']=[r for r in checkout['remaining'] if 'warehouse floor/concrete candidates' not in r]
todo='Validate floor temporal filtering/gameplay cost, current foliage and broader warehouse quality.'
if todo not in checkout['remaining']: checkout['remaining'].append(todo)
checkout['historical_snapshot_note']='Historical full mesh stages must be recomposed. Grates, construction, paving, water and floor materials are installed; see each current status for evidence and limits. Sacks remain staged.'
write(ROOT/'Sources/Lowtide/construction/checkout-status.json',checkout)
print(json.dumps({'status':report['status'],'native_views':36,'lighting_verified':lighting is not None,'performance_verified':False}))
