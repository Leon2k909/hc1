import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BASE = Path(__file__).resolve().parent
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, d): p.write_text(json.dumps(d, indent=2)+'\n', encoding='utf-8')
def rel(p): return p.relative_to(ROOT).as_posix()
m = read(BASE/'manifest.json')
for p, h in m['staged_files'].items():
    assert sha(ROOT/'Assets'/p) == h, p
for p, h in m['sources'].items():
    if p != 'Assets/materials/lowtide/lt_setts.vmat':
        assert sha(ROOT/p) == h, p
native = read(BASE/'production/verification.json')
assert native['TabRestored'] and not native['HasUnsavedChanges']
assert len(native['Slots']) == 3 and all(not s['HasOverride'] for s in native['Slots'])
canonical = read(BASE/'canonical-verification.json')
for p, h in canonical['generators'].items():
    assert sha(ROOT/p) == h
    ast.parse((ROOT/p).read_text(encoding='utf-8'))
assert not (ROOT/'Assets/materials/lowtide/paving-use/lt_setts_review.vmat').exists()
path = ROOT/'Sources/Lowtide/paving/use-status.json'
historical = BASE/'historical-use-status.json'
if not historical.exists():
    historical.write_bytes(path.read_bytes())
now = datetime.now(timezone.utc).isoformat()
status = dict(status='installed_native_visual_review_complete', observed_utc=now,
    project_root=str(ROOT), revision='paving-contact-use-v1-current-construction',
    production_changed=True, native_accepted=True, canonical_generator_integrated=True,
    generator='Tools/lowtide_paving_use.py', material_writer='Tools/lowtide_paving.py',
    refresh_command='rtk proxy python Tools/lowtide_paving_use.py --current --output output/lowtide/quality-pass/<new-folder>',
    installed_files={'Assets/'+p:h for p,h in m['staged_files'].items()},
    scope=dict(ground_triangles=m['ground_triangles'], wall_segments=m['wall_segments'],
               drain_outlets_over_paving=m['drains_over_setts'], grate_apertures=24,
               aperture_samples_clear=216, new_triangles=0, material_slots_added=0,
               texture_lookups_added=1, scene_changed=False, collision_changed=False),
    verification=dict(manifest=rel(BASE/'manifest.json'), source_data=rel(BASE/'verification.json'),
                      canonical=rel(BASE/'canonical-verification.json'), material_readback=rel(BASE/'material-readback.json'),
                      native_comparison=rel(BASE/'review/acceptance.json'), production_readback=rel(BASE/'production/verification.json'),
                      production_import=rel(BASE/'production-import.json')),
    reviewed_native_images=12,
    production_images={p.name:sha(p) for p in (BASE/'production').glob('*.png')},
    compiled_shader_present=(ROOT/'Assets/shaders/hc1_lowtide_paving_use.shader_c').exists(),
    project_compile_errors=0, native_paving_slots=3, temporary_review_material_archived=True,
    capture_restored_tab=native['RestoreTab'], capture_restored_play_state=False,
    historical_status=rel(historical), gameplay_performance_measured=False,
    temporal_review_complete=False, overall_AAA_verified=False,
    note='Narrow settled grit and local outlet moisture are installed. Original generated stone colour/PBR inputs and relief are unchanged. Current-layout regeneration reproduces all five installed files. Initial asynchronous shader loading warned before the compiler finished; subsequent native readback verifies the correct loaded shader and 2048-square mask. This is a static art layout, not a fluid simulation; broader map quality and controlled gameplay performance remain open.')
write(path,status)
checkout_path=ROOT/'Sources/Lowtide/construction/checkout-status.json'
checkout=read(checkout_path)
checkout.update(status='grates_construction_and_paving_installed_other_candidates_pending', observed_utc=now,
    latest_native_work='Sources/Lowtide/paving/use-status.json',
    native_work=['Sources/Lowtide/drainage/grate-status.json','Sources/Lowtide/construction/recomposed-status.json','Sources/Lowtide/paving/use-status.json'],
    historical_snapshot_note='Candidate/protected-file counts describe the earlier offline snapshot. Grates, construction and current-layout paving contact have since been installed and verified. Water and sacks remain staged; historical full-mesh snapshots must be recomposed against current sources.',
    remaining=['Review staged water filtering in the native scene before promotion.',
               'Recompose sack distance candidates against current sources; configure native grouping/switching and measure cost.',
               'Revalidate floor and foliage integration against the canonical checkout.',
               'Controlled gameplay performance, temporal behavior and overall visual quality remain open.'])
checkout['candidates']['paving-use'].update(native_accepted=True, current_installed_status='Sources/Lowtide/paving/use-status.json', historical_manifest_superseded=True)
write(checkout_path,checkout)
print(json.dumps({'installed_files_verified':5,'native_slots_verified':3,'native_images_reviewed':12,'grate_samples_clear':216,'overall_AAA_verified':False}))
