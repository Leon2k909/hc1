"""Tie the rebased exports to the unchanged reviewed geometry and image evidence."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


manifest = read(OUT/'manifest.json')
verification = read(OUT/'verification.json')
assert Path(manifest['project_root']).resolve() == ROOT
assert verification['manifest_sha256'] == sha(OUT/'manifest.json')
prior_path = ROOT/manifest['reused_components_manifest']
assert sha(prior_path) == manifest['reused_components_manifest_sha256']
prior = read(prior_path)
prior_check = read(prior_path.parent/'verification.json')
assert prior_check['manifest_sha256'] == sha(prior_path)
base_path = ROOT/manifest['baseline_manifest']
base = read(base_path)
prior_base = read(ROOT/prior['baseline_manifest'])
assert base['layout'] == prior_base['layout']
assert manifest['parameters'] == prior['parameters']
components = 0
for level, models in manifest['levels'].items():
    for name, entry in models.items():
        original = prior['levels'][level][name]
        assert sha(ROOT/entry['component']) == sha(ROOT/original['component']) == original['component_sha256']
        assert entry['triangles'] == original['triangles']
        assert base['models'][name]['component_sha256'] == prior_base['models'][name]['component_sha256']
        components += 1

preview = prior_path.parent/'preview'
provenance = read(preview/'provenance.json')
assert all(sha(preview/p) == h for p,h in provenance['previews'].items())
texture = 'Assets/materials/lowtide/sacks/lt_jute_color.png'
assert sha(ROOT/texture) == prior_base['protected'][texture] == base['protected'][texture]
for relative in ('Tools/lowtide_sack_preview.py', 'Tools/lowtide_window_software.py'):
    assert sha(ROOT/relative) == provenance['renderer_sources_sha256'][relative]
close_verification = read(base_path.parent/'verification.json')
unrelated = close_verification['preserved_triangles']
close_sacks = sum(v['new_triangles'] for v in base['models'].values())
totals = {'close': unrelated+close_sacks}
for level, models in manifest['levels'].items():
    totals['level-'+level] = unrelated+sum(v['triangles'] for v in models.values())
assert verification['preserved_triangles'] == unrelated*len(manifest['levels'])
report = dict(status='reviewed_distance_geometry_rebased_with_current_material_libraries', project_root=str(ROOT),
    manifest_sha256=sha(OUT/'manifest.json'), verification_sha256=sha(OUT/'verification.json'),
    prior_manifest=prior_path.relative_to(ROOT).as_posix(), prior_manifest_sha256=sha(prior_path),
    byte_identical_reviewed_components=components, original_jute_pixels_unchanged=True,
    reused_preview_provenance=(preview/'provenance.json').relative_to(ROOT).as_posix(),
    reused_preview_provenance_sha256=sha(preview/'provenance.json'),
    prior_screen_comparisons_sha256=sha(prior_path.parent/'verification.json'),
    newly_rendered_views=0, inspected_existing_views=['mouth-160.png', 'side-80.png', 'oblique-320.png'],
    preserved_triangles_per_detail_level=unrelated, full_aggregate_triangle_counts=totals,
    full_aggregate_reduction_fraction={name:1-value/totals['close'] for name,value in totals.items() if name!='close'},
    current_material_libraries=verification['current_material_libraries'],
    native_switching_configured=False, native_accepted=False, performance_verified=False,
    findings=['The medium candidate retains the sewn edge in the inspected mouth view.',
              'The lowest candidate loses that seam at larger screen sizes; its side silhouette remains close at 80 pixels.',
              'Six reviewed component files are byte-identical; new export checks cover current surrounding props and material libraries.'],
    limitations=['Screen comparisons are reused evidence for unchanged components, not new native captures.',
                 'Aggregate triangle savings are not frame-time results; grouping, switching distances and temporal appearance remain unverified.'])
(OUT/'rebase-verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k:report[k] for k in ('status','byte_identical_reviewed_components','current_material_libraries',
    'preserved_triangles_per_detail_level','full_aggregate_triangle_counts','full_aggregate_reduction_fraction')}, indent=2))
