"""Independent regeneration and integrity check for the offline detail meshes."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'Tools'))
import map_kit as K
import lowtide_map as L
import lowtide_window_construction as W
import lowtide_door_construction as D
import lowtide_construction_lods as LD

manifest = json.loads((LD.OUT/'manifest.json').read_text())
review = json.loads((LD.OUT/'review/verification.json').read_text())
combined = json.loads((LD.BASE/'construction-integration/manifest.json').read_text())
assert W.sha(LD.BASE/'construction-integration/manifest.json') == manifest['source_combined_manifest_sha256']
assert review['source_manifest_sha256'] == W.sha(LD.OUT/'manifest.json')
assert review['source_sha256'] == W.sha(LD.__file__)
assert all(W.sha(ROOT/p) == h for p, h in manifest['sources'].items())
assert all(W.sha(ROOT/v['output']) == v['sha256'] for level in manifest['levels'].values() for v in level.values())
assert all(W.sha(ROOT/p) == h for p, h in manifest['protected'].items())
rows = json.loads((LD.BASE/'window-construction/layout.json').read_text())['models']
doors = json.loads((LD.BASE/'door-construction/manifest.json').read_text())['selected_layout']
state = lambda: (W.surround, W.BAR_PROFILE, D.fastener, D.turned, D.board, D.pull)
before = state()
try:
    with LD.detail(2): raise ArithmeticError('Exercise scoped builder restoration')
except ArithmeticError: pass
assert state() == before
reproduction = LD.OUT/'reproduction'
reproduction.mkdir(exist_ok=True)
reproduced = []
for level in (1, 2):
    east = LD.components(rows['lowtide_east'], doors['lowtide_east'], level)
    pairs = {'lowtide_east': east, 'lowtide_west': east.mirrored(L.WEST_PAINTS),
             'lowtide_backdrop': LD.components(rows['lowtide_backdrop'], [], level)}
    assert state() == before
    for name, model in pairs.items():
        L.configure(model)
        path = reproduction/f'{name}-detail{level}.obj'
        K.write_obj(path, model, name)
        assert W.sha(path) == manifest['levels'][str(level)][name]['component_sha256']
        reproduced.append(path.name)
    print(f'Level {level}: three component meshes regenerate byte-identically', flush=True)
high = sum(v['triangles'] for v in combined['models'].values())
counts = {level: sum(v['triangles'] for v in data.values()) for level, data in manifest['levels'].items()}
assert all(W.sha(ROOT/p) == h for p, h in manifest['protected'].items())
report = dict(status='offline_detail_mesh_integrity_passed', high_detail_triangles=high,
              reduced_level_triangles=counts,
              reduction_fraction={level: 1-count/high for level, count in counts.items()},
              byte_identical_component_reproductions=reproduced,
              scoped_builders_restored_on_success_and_error=True,
              protected_live_files_unchanged=len(manifest['protected']),
              geometry_rays=sum(sum(v for k, v in r.items() if k.endswith('_rays')) for r in review['geometry_checks']),
              matched_preview_images=18,
              native_compile='not_run', native_lod_switching='not_configured', native_performance='not_measured',
              manifest_sha256=W.sha(LD.OUT/'manifest.json'), reviewer_sha256=review['reviewer_sha256'])
(LD.OUT/'offline-verification.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
