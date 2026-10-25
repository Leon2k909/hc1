"""Record the completed native crate-only change and its verification."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
def read(path): return json.loads(path.read_text())
def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()
def native(path):
    value = read(path)
    if 'structuredContent' in value: return value['structuredContent']
    rows = [json.loads(x['text']) for x in value['content'] if x['type'] == 'text']
    return rows[0] if len(rows) == 1 else rows

m = read(OUT/'stage-current/manifest.json')
receipt = read(OUT/'native-import.json')
assert receipt['Imported'] == 16 and receipt['EditorStatePreserved']
assert receipt['CoverBoxesRelocated'] == 6 and not receipt['SceneChanged']
assert all(native(OUT/f'compile-{side}/asset_compile.json')['Success'] for side in ('west', 'east'))
status = native(OUT/'status-after/editor_status.json')
assert status['LastCompileSucceeded'] and status['LastCompileErrors'] == 0
assert status['ActiveScenePath'].lower() == 'scenes/maps/belltower/belltower.scene'
assert not status['IsPlaying'] and not status['SceneHasUnsavedChanges']
canonical = read(OUT/'canonical-check.json')
assert all(row['old_faces_present'] == 0 and row['new_faces_present'] == row['new_faces_expected'] == 15188
           for row in canonical.values()) and len(canonical) == 2
for name, row in m['files'].items():
    if name.endswith(('/belltower_east.obj', '/belltower_west.obj')): continue
    assert sha(ROOT/name) == row['after'], name
map_text = (ROOT/'Tools/belltower_map.py').read_text()
assert map_text.count('MarketCratesV3.stack( model, rng, Place, WOOD )') == 1
assert 'import belltower_market_crates_v3 as MarketCratesV3' in map_text
traces = native(OUT/'trace-after/call_tools.json')
assert len(traces) == 12
for index, trace in enumerate(traces):
    expected = 0 if index % 2 == 0 else 36 if index % 6 == 1 else 84
    assert trace['Hit'] and not trace['StartedSolid']
    assert abs(float(trace['EndPosition'].split(',')[2])-expected) < .001
captures = {}
for phase, view in [('before','wide'), ('after','wide'), ('after','detail')]:
    directory = ROOT/f'output/belltower/quality/market-crates-v3-{phase}'
    restored = read(directory/f'{view}-restore.json')
    assert all(restored.values())
    captures[phase+'_'+view] = (directory/f'{view}.png').relative_to(ROOT).as_posix()
source_check = read(OUT/'source-validation.json')
assert source_check['rng_preserved_seeds'] == 128
geometry = read(OUT/'geometry-validation.json')['geometry']
report = {
    'revision': 'market-crates-v3', 'status': 'applied-and-verified', 'date': '2026-10-21',
    'scope': 'The pictured three Market Street shipping crates and their mirrored copy.',
    'placement': 'Compact stall-side storage: two ground crates, one supported on the larger crate; lamp and alley clear.',
    'appearance': ['shallow board bow and cup', 'chamfered and chipped plank edges', 'slight fastener variation', 'existing photographed wood materials'],
    'placements_west': m['placements_west'], 'east_is_mirrored': True,
    'authoring_module': 'Tools/belltower_market_crates_v3.py',
    'generator_hook': 'MarketCratesV3.stack in Tools/belltower_map.py; preserves later prop random draws.',
    'import': receipt, 'models_compiled': ['belltower_west.vmdl', 'belltower_east.vmdl'],
    'collision': {'probes_passed': 12, 'old_positions_ground_height': 0, 'new_visible_top_heights': [36,84], 'relocated_boxes': 6},
    'source_random_sequence': source_check, 'geometry': geometry,
    'unrelated_geometry_preserved_at_publication': True,
    'concurrent_authoring_updates': 'Canonical OBJs also received unrelated updates; direct face matching confirms all replacement crate faces remain and old faces are absent.',
    'canonical_group_inspection': canonical,
    'private_mesh_bounded_import_and_model_hashes_verified': True,
    'captures': captures, 'capture_camera_and_scene_state_restored': True,
    'last_editor_check': {'compile_errors': 0, 'scene': status['ActiveScenePath'], 'unsaved': False, 'playing': False},
    'manifest': 'output/belltower/crates-v3-20261021/stage-current/manifest.json',
}
destination = ROOT/'Sources/Belltower/crates/market-stack-v3-20261021.json'
data = json.dumps(report, indent=2)+'\n'
assert not destination.exists() or destination.read_text() == data
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(data)
(OUT/'validation.json').write_text(data)
print(json.dumps({'status': report['status'], 'crates': 6, 'collision_probes': 12, 'models_compiled': 2,
                  'metadata': destination.relative_to(ROOT).as_posix()}))
