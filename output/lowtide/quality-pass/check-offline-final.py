"""Final offline handoff integrity and owned-process inventory."""
import hashlib
import json
import os
from pathlib import Path
import platform

platform._wmi_query = lambda *a, **k: (_ for _ in ()).throw(OSError('offline platform fallback'))
import psutil

root = Path(__file__).resolve().parents[3]
base = root/'output/lowtide/quality-pass'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
combined = json.loads((base/'construction-integration/manifest.json').read_text())
assert all(sha(root/p) == digest for p, digest in combined['source_manifests'].items())
assert all(sha(base/'construction-integration/stage'/p) == value['after'] for p, value in combined['changes'].items())
assert all(sha(root/p) == value for p, value in combined['protected'].items())
assert sha(root/'Tools/lowtide_construction_stage.py') == combined['generator_sha256']
door = json.loads((base/'door-construction/verification.json').read_text())
assert door['manifest_sha256'] == sha(base/'door-construction/manifest.json')
assert door['verifier_sha256'] == sha(root/'Tools/lowtide_door_verify.py')
preview = json.loads((base/'door-construction/preview/cpu-provenance.json').read_text())
assert preview['geometry_generator_sha256'] == sha(root/'Tools/lowtide_door_construction.py')
assert preview['renderer_sha256'] == sha(root/'Tools/lowtide_window_software.py')
assert all(sha(base/f'door-construction/preview/{name}.obj') == digest for name, digest in preview['exported_meshes'].items())
status = json.loads((root/'Sources/Lowtide/construction/offline-status.json').read_text())
assert combined['delta_triangles'] == status['combined_models']['total_added_triangles']
brick = json.loads((root/'Sources/Lowtide/brick/relief-status.json').read_text())
assert not brick['accepted_for_native_integration']
files = [root/'Tools'/name for name in ('lowtide_brick_relief.py', 'lowtide_brick_relief_preview.py',
         'lowtide_door_construction.py', 'lowtide_door_preview.py', 'lowtide_door_verify.py',
         'lowtide_construction_stage.py', 'lowtide_window_software.py',
         'lowtide_construction_lods.py', 'lowtide_construction_lod_review.py',
         'lowtide_warehouse_floor.py', 'lowtide_warehouse_floor_review.py',
         'lowtide_concrete_wear.py', 'lowtide_concrete_wear_review.py', 'lowtide_material_stage.py',
         'lowtide_sack_construction.py', 'lowtide_sack_preview.py', 'lowtide_sack_verify.py',
         'lowtide_sack_lods.py', 'lowtide_sack_lod_review.py',
         'lowtide_drain_construction.py', 'lowtide_drain_review.py',
         'lowtide_drain_junctions.py', 'lowtide_drain_junction_verify.py', 'lowtide_drain_context.py',
         'lowtide_paving_use.py', 'lowtide_paving_use_review.py',
         'lowtide_water_filter.py', 'lowtide_water_filter_review.py')]
assert all(not line.rstrip('\r\n').endswith((' ', '\t')) for p in files for line in p.read_text().splitlines(keepends=True))
owned = []
queries = []
for process in psutil.process_iter(['pid', 'name', 'cmdline']):
    if process.pid == os.getpid(): continue
    command = process.info['cmdline'] or []
    if process.info['name'].lower() == 'python.exe' and any(str(part).replace('\\', '/').endswith(p.name) for part in command for p in files):
        owned.append(dict(pid=process.pid, command=command))
    if process.info['name'].lower() in ('dotnet.exe', 'msbuild.exe') and any(
            'water-filter/compile' in str(part).replace('\\', '/').lower() for part in command):
        owned.append(dict(pid=process.pid, command=command))
    if process.info['name'].lower() == 'powershell.exe' and any('Get-CimInstance Win32_Process' in part and 'python|blender' in part for part in command):
        queries.append(dict(pid=process.pid, command=command))
assert not owned, owned
report = dict(status='offline_handoff_integrity_passed', production_files_unchanged=len(combined['protected']),
              combined_models=len(combined['changes']), combined_delta_triangles=combined['delta_triangles'],
              previews_match_current_sources=True, geometry_checks_bound_to_current_manifest=True,
              rejected_brick_excluded=True, active_owned_build_or_preview_processes=owned,
              lingering_owned_process_queries=queries, native_checks='Deferred by user request')
lod_path = base/'construction-lods/manifest.json'
if lod_path.exists():
    lod = json.loads(lod_path.read_text())
    checked = json.loads((base/'construction-lods/offline-verification.json').read_text())
    assert checked['manifest_sha256'] == sha(lod_path)
    assert all(sha(root/p) == h for p, h in lod['sources'].items())
    assert all(sha(root/v['output']) == v['sha256'] for level in lod['levels'].values() for v in level.values())
    assert sha(root/'Tools/lowtide_construction_lod_review.py') == checked['reviewer_sha256']
    report['reduced_detail_levels_verified'] = checked['reduced_level_triangles']
    report['native_lod_switching'] = 'Not configured'
floor_path = base/'warehouse-floor/manifest.json'
if floor_path.exists():
    floor = json.loads(floor_path.read_text())
    checked = json.loads((base/'warehouse-floor/offline-verification.json').read_text())
    preview = json.loads((base/'warehouse-floor/preview/provenance.json').read_text())
    assert checked['manifest_sha256'] == preview['manifest_sha256'] == sha(floor_path)
    assert checked['reviewer_sha256'] == preview['renderer_sha256'] == sha(root/'Tools/lowtide_warehouse_floor_review.py')
    assert all(sha(root/p) == value for p, value in floor['sources'].items())
    assert all(sha(root/p) == value for p, value in floor['protected'].items())
    assert all(sha(base/'warehouse-floor/stage'/p) == value for p, value in floor['staged_files'].items())
    assert all(sha(base/'warehouse-floor/preview'/p) == value for p, value in preview['previews'].items())
    assert floor['source_color_sha256'] == floor['staged_color_sha256']
    assert not floor['production_changed'] and floor['geometry_changes'] == 0
    reproduction = json.loads((base/'warehouse-floor/reproduction-verification.json').read_text())
    assert reproduction['manifest_sha256'] == sha(floor_path)
    assert sha(base/'warehouse-floor/reproduction/manifest.json') == sha(floor_path)
    assert all(sha(base/'warehouse-floor/reproduction/stage'/p) == value for p, value in floor['staged_files'].items())
    report['warehouse_floor'] = dict(staged_files=len(floor['staged_files']),
        protected_files=len(floor['protected']), source_color_preserved=True,
        geometry_changes=0, reproduced_files=reproduction['byte_identical_files'],
        native_checks='Deferred; offline material candidate')
wear_path = base/'concrete-wear/manifest.json'
if wear_path.exists():
    wear = json.loads(wear_path.read_text())
    checked = json.loads((base/'concrete-wear/offline-verification.json').read_text())
    preview = json.loads((base/'concrete-wear/preview/provenance.json').read_text())
    reproduction = json.loads((base/'concrete-wear/reproduction-verification.json').read_text())
    assert checked['manifest_sha256'] == preview['manifest_sha256'] == reproduction['manifest_sha256'] == sha(wear_path)
    assert checked['reviewer_sha256'] == preview['renderer_sha256'] == sha(root/'Tools/lowtide_concrete_wear_review.py')
    assert checked['shared_renderer_sha256'] == preview['shared_renderer_sha256'] == sha(root/'Tools/lowtide_warehouse_floor_review.py')
    assert all(sha(root/p) == value for p, value in wear['sources'].items())
    assert all(sha(root/p) == value for p, value in wear['protected'].items())
    assert all(sha(base/'concrete-wear/stage'/p) == sha(base/'concrete-wear/reproduction/stage'/p) == value for p, value in wear['staged_files'].items())
    assert all(sha(base/'concrete-wear/preview'/p) == value for p, value in preview['previews'].items())
    assert sha(base/'concrete-wear/reproduction/manifest.json') == sha(wear_path)
    assert checked['other_surface_scope_excluded'] and checked['untouched_floor_material_samples'] == 32
    assert not wear['production_changed'] and wear['new_geometry'] == 0
    report['concrete_use'] = dict(staged_files=len(wear['staged_files']), protected_files=len(wear['protected']),
        route_samples=checked['path_samples'], atlas_samples=checked['atlas_texel_samples'],
        reproduced_files=reproduction['byte_identical_files'], native_checks='Deferred; offline material candidate')
materials_path = base/'material-integration/manifest.json'
if materials_path.exists():
    materials = json.loads(materials_path.read_text())
    assert all(sha(root/p) == value for p, value in materials['source_manifests'].items())
    assert sha(root/'Tools/lowtide_material_stage.py') == materials['generator_sha256']
    assert all(sha(base/'material-integration/stage'/p) == value for p, value in materials['assets'].items())
    assert all(sha(root/'Assets'/p) == value['before'] for p, value in materials['models'].items())
    assert all(sha(root/p) == value for p, value in materials['protected'].items())
    assert status['combined_materials']['existing_slot_remaps'] == len(materials['material_remap_plan']) == 4
    assert status['combined_materials']['staged_files'] == len(materials['assets']) == 20
    report['combined_materials'] = dict(staged_files=20, existing_slot_remaps=4, model_snapshots=2,
        native_checks='Deferred; apply only scoped remaps after fresh validation')
sack_path = base/'sack-construction/manifest.json'
if sack_path.exists():
    sack = json.loads(sack_path.read_text())
    checked = json.loads((base/'sack-construction/verification.json').read_text())
    preview = json.loads((base/'sack-construction/final-preview/provenance.json').read_text())
    saved = json.loads((root/'Sources/Lowtide/sacks/construction-status.json').read_text())
    assert saved['evidence']['manifest_sha256'] == checked['manifest_sha256'] == sha(sack_path)
    assert checked['verifier_sha256'] == sha(root/'Tools/lowtide_sack_verify.py')
    assert checked['preview_renderer_sha256'] == preview['reviewer_sha256'] == sha(root/'Tools/lowtide_sack_preview.py')
    assert preview['generator_sha256'] == sha(root/'Tools/lowtide_sack_construction.py')
    assert checked['shared_renderer_sha256'] == preview['renderer_sha256'] == sha(root/'Tools/lowtide_window_software.py')
    assert all(sha(root/p) == h for p, h in sack['sources'].items())
    assert all(sha(root/p) == h for p, h in sack['protected'].items())
    assert all(sha(root/'Assets'/p) == v['before'] and sha(base/'sack-construction/stage'/p) == v['after'] for p, v in sack['changes'].items())
    assert all(sha(base/'sack-construction/reproduction'/f'{name}-sacks.obj') == v['component_sha256'] for name, v in sack['models'].items())
    assert all(sha(base/'sack-construction/final-preview'/p) == h for p, h in preview['previews'].items())
    assert not saved['integration']['native_accepted'] and not sack['production_changed']
    assert status['separate_pending_work']['sewn_cargo_sacks'] == 'Sources/Lowtide/sacks/construction-status.json'
    report['sewn_cargo_sacks'] = dict(sacks=checked['sacks'], closed_mesh_triangles=checked['triangles'],
        protected_live_files=len(sack['protected']), delta_triangles=sack['delta_triangles'],
        reproduced_components=checked['byte_identical_reproduced_components'],
        native_checks='Deferred; visual acceptance and geometry cost unverified')
sack_lods_path = base/'sack-lods/manifest.json'
if sack_lods_path.exists():
    lod = json.loads(sack_lods_path.read_text())
    checked = json.loads((base/'sack-lods/verification.json').read_text())
    preview = json.loads((base/'sack-lods/preview/provenance.json').read_text())
    saved = json.loads((root/'Sources/Lowtide/sacks/lod-status.json').read_text())
    assert checked['manifest_sha256'] == saved['evidence']['manifest_sha256'] == sha(sack_lods_path)
    assert checked['reviewer_sha256'] == sha(root/'Tools/lowtide_sack_lod_review.py')
    assert lod['baseline_manifest_sha256'] == sha(base/'sack-construction/manifest.json')
    assert all(sha(root/p) == h for p, h in lod['sources'].items())
    assert all(sha(root/p) == h for p, h in lod['protected'].items())
    assert all(sha(root/p) == h for p, h in preview['geometry_sources_sha256'].items())
    assert all(sha(root/p) == h for p, h in preview['renderer_sources_sha256'].items())
    assert all(sha(base/'sack-lods/preview'/p) == h for p, h in preview['previews'].items())
    assert all(sha(root/v['component']) == v['component_sha256'] and sha(root/v['staged']) == v['staged_sha256'] for models in lod['levels'].values() for v in models.values())
    assert all(sha(root/p) == sha(root/v['source']) == v['sha256'] for p, v in saved['material_library_dependencies'].items())
    assert not lod['native_switching_configured'] and not saved['native_switching_configured']
    assert status['separate_pending_work']['sack_detail_candidates'] == 'Sources/Lowtide/sacks/lod-status.json'
    report['sack_detail_candidates'] = dict(closed_meshes=checked['closed_sacks'],
        lower_sack_triangles=checked['reduced_sack_triangles'],
        retained_vertex_attributes=checked['retained_vertex_attributes'],
        native_switching_configured=False, native_checks='Deferred; grouping, transitions and performance unverified')
drain_path = base/'drain-construction/manifest.json'
if drain_path.exists():
    drain = json.loads(drain_path.read_text())
    checked = json.loads((base/'drain-construction/verification.json').read_text())
    preview = json.loads((base/'drain-construction/preview/provenance.json').read_text())
    saved = json.loads((root/'Sources/Lowtide/drainage/construction-status.json').read_text())
    assert saved['evidence']['manifest_sha256'] == checked['manifest_sha256'] == preview['manifest_sha256'] == sha(drain_path)
    assert checked['verifier_sha256'] == preview['reviewer_sha256'] == sha(root/'Tools/lowtide_drain_review.py')
    assert preview['geometry_generator_sha256'] == sha(root/'Tools/lowtide_drain_construction.py')
    assert preview['renderer_sha256'] == sha(root/'Tools/lowtide_window_software.py')
    assert preview['shadow_adapter_sha256'] == sha(root/'Tools/lowtide_sack_preview.py')
    assert all(sha(root/p) == h for p, h in drain['sources'].items())
    assert all(sha(root/p) == h for p, h in drain['protected'].items())
    assert all(sha(base/'drain-construction'/p) == h for p, h in drain['components'].items())
    assert all(sha(root/'Assets'/p) == v['before'] and sha(base/'drain-construction/stage'/p) == v['after'] for p, v in drain['changes'].items())
    assert all(sha(base/'drain-construction/stage'/p) == sha(base/'drain-construction/reproduction/stage'/p) == h for p, h in drain['staged_material_changes']['files'].items())
    assert all(sha(root/'Assets'/p) == v['before'] for p, v in drain['staged_material_changes']['changes'].items())
    assert sha(base/'drain-construction/reproduction/drains-new.obj') == drain['components']['drains-new.obj']
    assert all(sha(base/'drain-construction/preview'/p) == h for p, h in preview['previews'].items())
    assert all(sha(base/'drain-construction/preview'/p) == h for p, h in preview['meshes'].items())
    library = drain['material_library']
    assert sha(root/library['source']) == sha(base/'drain-construction'/library['staged']) == library['sha256']
    assert not saved['native_accepted'] and not saved['production_changed']
    assert status['separate_pending_work']['drainage_construction_and_atlas_mapping'] == 'Sources/Lowtide/drainage/construction-status.json'
    report['drainage'] = dict(pipes=checked['pipes'], candidate_triangles=checked['triangles'],
        delta_triangles=drain['delta_triangles'], aperture_ray_samples=checked['aperture_ray_samples'],
        atlas_mapping_samples=checked['atlas_mapping_samples'], source_pixels_preserved=True,
        reproduced_material_files=checked['byte_identical_reproduced_material_files'],
        native_checks='Deferred; shader compilation, map connections, geometry and shadow cost unverified')
junction_path = base/'drain-junctions/manifest.json'
if junction_path.exists():
    junction = json.loads(junction_path.read_text())
    checked = json.loads((base/'drain-junctions/verification.json').read_text())
    preview = json.loads((base/'drain-junctions/preview/provenance.json').read_text())
    saved = json.loads((root/'Sources/Lowtide/drainage/junction-status.json').read_text())
    previous = json.loads((root/'Sources/Lowtide/drainage/construction-status.json').read_text())
    assert checked['manifest_sha256'] == saved['evidence']['manifest_sha256'] == sha(junction_path)
    assert checked['verifier_sha256'] == sha(root/'Tools/lowtide_drain_junction_verify.py')
    assert junction['baseline_manifest_sha256'] == sha(root/junction['baseline_manifest'])
    assert all(sha(root/p) == h for p, h in junction['sources'].items())
    assert all(sha(root/p) == h for p, h in junction['protected'].items())
    assert all(sha(base/'drain-junctions'/p) == h for p, h in junction['components'].items())
    assert all(sha(base/'drain-junctions/stage'/p) == h for p, h in junction['staged_files'].items())
    assert sha(base/'drain-junctions/reproduction/junctions-new.obj') == junction['components']['junctions-new.obj']
    assert all(sha(root/p) == h for p, h in checked['saved_architecture_sources'].items())
    assert all(sha(root/p) == h for p, h in preview['source_files'].items())
    assert all(sha(root/p) == h for p, h in preview['metal_inputs'].items())
    assert preview['reviewer_sha256'] == sha(root/'Tools/lowtide_drain_context.py')
    assert preview['renderer_sha256'] == sha(root/'Tools/lowtide_window_software.py')
    assert preview['shadow_adapter_sha256'] == sha(root/'Tools/lowtide_sack_preview.py')
    assert all(sha(base/'drain-junctions/preview'/p) == h for p, h in preview['previews'].items())
    assert not saved['native_accepted'] and not saved['production_changed']
    assert previous['geometry']['direct_promotion_superseded']
    assert previous['integration']['current_composed_junction_candidate'] == status['separate_pending_work']['drainage_junctions'] == 'Sources/Lowtide/drainage/junction-status.json'
    report['drainage_junctions'] = dict(warehouse_heads=20, shed_receivers=16, gutters=8,
        delta_from_live=junction['delta_from_live'], clearance_rays=checked['clearance_rays'],
        minimum_sampled_clearance_inches=checked['minimum_sampled_clearance_inches'],
        shed_flow_rays=checked['shed_flow_rays'], staged_files=len(junction['staged_files']),
        native_checks='Deferred; full-map appearance, compilation, geometry/shadow cost and persistence unverified')
paving_path = base/'paving-use/manifest.json'
if paving_path.exists():
    paving = json.loads(paving_path.read_text())
    checked = json.loads((base/'paving-use/verification.json').read_text())
    preview = json.loads((base/'paving-use/preview/provenance.json').read_text())
    saved = json.loads((root/'Sources/Lowtide/paving/use-status.json').read_text())
    reproduced = json.loads((base/'paving-use/reproduction-verification.json').read_text())
    assert saved['evidence']['manifest_sha256'] == checked['manifest_sha256'] == preview['manifest_sha256'] == reproduced['manifest_sha256'] == sha(paving_path)
    assert checked['reviewer_sha256'] == preview['renderer_sha256'] == sha(root/'Tools/lowtide_paving_use_review.py')
    assert all(sha(root/p) == h for p, h in paving['sources'].items())
    assert all(sha(root/p) == h for p, h in paving['protected'].items())
    assert all(sha(base/'paving-use/stage'/p) == sha(base/'paving-use/reproduction/stage'/p) == h for p, h in paving['staged_files'].items())
    assert sha(paving_path) == sha(base/'paving-use/reproduction/manifest.json')
    assert all(sha(base/'paving-use/preview'/p) == h for p, h in preview['files'].items())
    assert all(sha(root/p) == h for p, h in preview['source_geometry'].items())
    assert all(sha(root/p) == h for p, h in preview['renderer_dependencies'].items())
    assert all(sha(root/'Assets'/p) == h for p, h in preview['original_texture_inputs'].items())
    assert sha(root/saved['atlas_audit']['report']) == saved['atlas_audit']['report_sha256']
    assert all((sha(root/'Assets'/p) == h if h else not (root/'Assets'/p).exists())
               for p, h in saved['integration']['live_target_states'].items())
    assert not saved['production_changed'] and not saved['native_accepted']
    assert status['separate_pending_work']['exterior_paving_contact'] == 'Sources/Lowtide/paving/use-status.json'
    report['exterior_paving_contact'] = dict(staged_files=len(paving['staged_files']),
        protected_live_files=len(paving['protected']), atlas_samples=checked['atlas_samples'],
        excluded_surface_samples=checked['excluded_surface_samples'],
        moisture_texels_checked=checked['moisture_texels_checked'],
        drain_outlets_over_setts=checked['drain_outlets_over_setts'],
        delta_triangles=0, new_material_slots=0, extra_texture_lookups=1,
        native_checks='Deferred; shader compilation, appearance, filtering, performance and persistence unverified')
water_path = base/'water-filter/manifest.json'
if water_path.exists():
    water = json.loads(water_path.read_text())
    checked = json.loads((base/'water-filter/verification.json').read_text())
    preview = json.loads((base/'water-filter/preview/provenance.json').read_text())
    saved = json.loads((root/'Sources/Lowtide/water/filter-status.json').read_text())
    reproduced = json.loads((base/'water-filter/reproduction-verification.json').read_text())
    compiled = json.loads((base/'water-filter/compile-verification.json').read_text())
    first = json.loads((base/'water-filter/first-review/manifest.json').read_text())
    assert saved['evidence']['manifest_sha256'] == checked['manifest_sha256'] == preview['manifest_sha256'] == reproduced['manifest_sha256'] == compiled['manifest_sha256'] == sha(water_path)
    assert checked['reviewer_sha256'] == preview['renderer_sha256'] == sha(root/'Tools/lowtide_water_filter_review.py')
    assert all(sha(root/p) == h for p, h in water['sources'].items())
    assert all(sha(root/p) == h for p, h in water['protected'].items())
    assert all(sha(Path(p)) == h for p, h in water['api']['external_sources'].items())
    assert all(sha(base/'water-filter/stage'/p) == sha(base/'water-filter/reproduction/stage'/p) == h for p, h in water['staged_files'].items())
    assert sha(water_path) == sha(base/'water-filter/reproduction/manifest.json')
    assert all(sha(base/'water-filter/preview'/p) == h for p, h in preview['files'].items())
    assert all(sha(root/p) == h for p, h in preview['source_image'].items())
    assert all((sha(root/p) == h if h else not (root/p).exists()) for p, h in water['live_before'].items())
    assert saved['integration']['live_target_states'] == water['live_before']
    assert all(sha(base/'water-filter'/p) == h for p, h in compiled['files'].items())
    assert all(sha(Path(p)) == h for p, h in compiled['reference_files'].items())
    assert compiled['source_sha256'] == first['staged_files'][compiled['source']] == water['staged_files'][compiled['source']]
    assert compiled['warnings'] == compiled['errors'] == 0
    assert not compiled['loaded_into_engine'] and not compiled['shader_compiled']
    assert not saved['production_changed'] and not saved['native_accepted'] and not water['code_changed']
    assert not preview['native_engine_capture'] and not preview['actual_lowtide_scene']
    assert saved['first_review']['rejected'] and saved['scope']['roughness_filter_scale'] == water['roughness_filter_scale'] == .35
    assert status['separate_pending_work']['water_reflection_filtering'] == 'Sources/Lowtide/water/filter-status.json'
    report['water_reflection_filtering'] = dict(staged_files=len(water['staged_files']),
        protected_live_files=len(water['protected']), max_mips=water['max_mips'],
        roughness_filter_scale=water['roughness_filter_scale'], isolated_csharp_compile='0 warnings, 0 errors',
        constant_hdr_cases=checked['constant_hdr_cases'], zero_lod_samples=checked['zero_lod_samples'],
        roughness_projection_cases=checked['roughness_projection_cases'],
        single_mip_fallback_cases=checked['single_mip_fallback_cases'],
        derivative_only_cases=checked['derivative_only_cases'],
        additional_960x540_color_bytes=saved['scope']['additional_color_bytes_at_960x540'],
        native_checks='Deferred; shader/sandbox compile, GPU lifecycle, scene appearance, temporal response and performance unverified')
(base/'construction-integration/final-offline-check.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
