"""Package material-library dependencies and save reviewed offline LOD evidence."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+'\n')

manifest = json.loads((OUT/'manifest.json').read_text())
checked = json.loads((OUT/'verification.json').read_text())
preview = json.loads((OUT/'preview/provenance.json').read_text())
assert checked['manifest_sha256'] == sha(OUT/'manifest.json')
assert checked['reviewer_sha256'] == sha(ROOT/'Tools/lowtide_sack_lod_review.py')
assert all(sha(ROOT/p) == h for p, h in manifest['sources'].items())
assert all(sha(ROOT/p) == h for p, h in manifest['protected'].items())
assert all(sha(ROOT/p) == h for p, h in preview['geometry_sources_sha256'].items())
assert all(sha(ROOT/p) == h for p, h in preview['renderer_sources_sha256'].items())
assert all(sha(OUT/'preview'/p) == h for p, h in preview['previews'].items())
dependencies = {}
for level, models in manifest['levels'].items():
    for name, entry in models.items():
        target = ROOT/entry['staged']
        assert sha(target) == entry['staged_sha256']
        library = ROOT/'Assets/models/maps/lowtide'/f'{name}.mtl'
        assert sha(library) == manifest['protected'][library.relative_to(ROOT).as_posix()]
        assert f'mtllib {library.name}\n' in target.read_text()
        staged_library = target.with_name(library.name)
        assert staged_library.resolve().is_relative_to(OUT.resolve())
        shutil.copy2(library, staged_library)
        assert sha(staged_library) == sha(library)
        dependencies[staged_library.relative_to(ROOT).as_posix()] = dict(source=library.relative_to(ROOT).as_posix(), sha256=sha(library))
maxima = {f'level-{level}-{size}px':max(r['max_edge_pixels'] for r in checked['silhouette_comparisons'] if r['level']==level and r['size']==size)
          for level in (1, 2) for size in (320, 160, 80)}
status = dict(date='2026-10-15', revision=manifest['revision'],
    status='offline_detail_candidates_reviewed', native_switching_configured=False,
    production_changed=False, close_candidate_changed=False,
    generator='Tools/lowtide_sack_lods.py', reviewer='Tools/lowtide_sack_lod_review.py',
    geometry=dict(sacks=264, close_triangles_per_sack=1570,
        lower_triangles_per_sack={level:next(iter(models.values()))['per_sack_triangles'] for level, models in manifest['levels'].items()},
        lower_total_sack_triangles=checked['reduced_sack_triangles'],
        retained_attributes='Every exported lower-detail vertex position, cloth UV and shading normal occurs in the reviewed close mesh.',
        simplification='Retains extra vertices around pinched corners. The medium mesh keeps simplified closed seams; the far mesh omits thread shells. Full close geometry stays intact.'),
    evidence=dict(manifest='output/lowtide/quality-pass/sack-lods/manifest.json', manifest_sha256=sha(OUT/'manifest.json'),
        verification='output/lowtide/quality-pass/sack-lods/verification.json',
        previews='output/lowtide/quality-pass/sack-lods/preview/provenance.json',
        closed_meshes_checked=checked['closed_sacks'], vertex_attributes_checked=checked['retained_vertex_attributes'],
        protected_live_files=len(manifest['protected']), silhouette_comparisons=len(checked['silhouette_comparisons']),
        max_silhouette_error_pixels=maxima),
    preview=dict(native_engine_capture=False, reviewed='Nine comparison sheets cover the sewn end, side and oblique views at 320/160/80 pixels.',
                 filtering='CPU nearest-mip choice from each triangle footprint; source albedo files remain unchanged.',
                 limitations=preview['limitations']),
    material_library_dependencies=dependencies,
    integration=dict(native_accepted=False, next=[
        'Retain offline mode until the user resumes native work; refresh before hashes and editor state.',
        'Profile the close sacks in an actual match before choosing budgets.',
        'The three source meshes aggregate many props. Choose per-stack grouping/instancing or an appropriate ModelDoc strategy before assigning screen or distance thresholds.',
        'Reuse the existing model material remaps and collision. Each staged alternative includes its unchanged original material library.',
        'Check temporal transitions, textile filtering, silhouette changes, draw calls and gameplay cost in the normal viewport; save and verify persistence after acceptance.']),
    overall_goal='Open; lower triangle counts do not establish native performance or AAA quality')
write(ROOT/'Sources/Lowtide/sacks/lod-status.json', status)
high_path = ROOT/'Sources/Lowtide/sacks/construction-status.json'
high = json.loads(high_path.read_text())
high['integration']['distance_detail_candidates'] = 'Sources/Lowtide/sacks/lod-status.json'
write(high_path, high)
main_path = ROOT/'Sources/Lowtide/construction/offline-status.json'
main = json.loads(main_path.read_text())
main['separate_pending_work']['sack_detail_candidates'] = 'Sources/Lowtide/sacks/lod-status.json'
write(main_path, main)
print(json.dumps(dict(lower_triangles=status['geometry']['lower_triangles_per_sack'], max_silhouette_error_pixels=maxima,
                      native_switching_configured=False, material_libraries=len(dependencies)), indent=2))
