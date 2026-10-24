"""Verify the garden placement edit against its exact saved-scene and model baseline."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/belltower/bush-grounding'
SCENE = ROOT / 'Assets/scenes/maps/Belltower/belltower.scene'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def differences(a, b, path=''):
    if type(a) != type(b):
        yield path, a, b
    elif isinstance(a, dict):
        for key in sorted(a.keys() | b.keys()):
            if key not in a or key not in b:
                yield path + '/' + key, a.get(key), b.get(key)
            else:
                yield from differences(a[key], b[key], path + '/' + key)
    elif isinstance(a, list):
        if len(a) != len(b):
            yield path + '/length', len(a), len(b)
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                yield from differences(x, y, path + '/' + str(i))
    elif a != b:
        yield path, a, b


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene-only', action='store_true')
    parser.add_argument('--offline', action='store_true', help='Check the closed-editor save; native appearance remains pending.')
    parser.add_argument('--scene', type=Path, default=SCENE, help='Explicit archived checkpoint when later shared edits have advanced the live scene.')
    parser.add_argument('--input-root', type=Path, help='Explicit archived input overlay; every archived file must still match its recorded checksum.')
    args = parser.parse_args()
    plan = json.loads((OUT / 'plan.json').read_text())
    original = OUT / 'before/Assets/scenes/maps/Belltower/belltower.scene'
    assert sha(original) == plan['before_scene_sha256']
    for path, expected in (plan['model_guards'] | plan['source_after']).items():
        archived = args.input_root / path if args.input_root else None
        checked = archived if archived and archived.is_file() else ROOT / path
        assert sha(checked) == expected, path
    before = json.loads(original.read_text())
    expected = copy.deepcopy(before)
    for row in plan['objects']:
        parts = row['path'].strip('/').split('/')
        obj = expected
        for part in parts:
            obj = obj[int(part)] if isinstance(obj, list) else obj[part]
        assert obj['__guid'] == row['id']
        assert obj['Position'] == row['old_position'] and obj['Scale'] == row['old_scale']
        obj['Position'], obj['Scale'] = row['position'], row['scale']
    scene = args.scene.resolve()
    current = json.loads(scene.read_text())
    unexpected = list(differences(expected, current))
    if unexpected:
        (OUT / 'unexpected-save-diff.json').write_text(json.dumps(unexpected, indent=2) + '\n')
        raise AssertionError(f'{len(unexpected)} unexpected saved values: {unexpected[:5]}')
    for row in plan['objects']:
        position = list(map(float, row['position'].split(',')))
        scale = list(map(float, row['scale'].split(',')))
        assert abs(position[2] + scale[2] * plan['root_anchor_local_z'] - (row['ground_z'] - .5)) < .001
        assert abs(position[2] + scale[2] * plan['model_top_local_z'] - row['preserved_top_z']) < .001
    if not args.offline:
        native = json.loads((OUT / 'native-verification.json').read_text())
        assert native['Verified'] == 244 and native['Saved'] and native['TargetObjectIdentitiesPreserved']
        assert native['MaxRootContactError'] < .001 and native['MaxCanopyTopError'] < .001
    generator = json.loads((OUT / 'generator-check.json').read_text())
    assert generator['polygons_collision_boxes_hulls_exact'] and generator['changed_garden_shrubs_per_half'] == 122
    result = {'before_scene_sha256': sha(original), 'after_scene_sha256': sha(scene),
        'checked_scene_path': str(scene),
        'garden_plants_corrected': 244, 'position_and_vertical_scale_only': True,
        'all_other_scene_values_exact': True, 'town_models_match_verified_input_revision': True,
        'input_revision': plan.get('input_revision', 1),
        'town_models_unchanged_by_bush_placement': True,
        'planter_gate_clock_assets_and_placements_preserved': True,
        'source_geometry_collision_preserved': True, 'saved_roots_and_tops_verified': True,
        'native_roots_and_tops_verified': not args.offline,
        'native_visual_review_verified': False, 'capture_restoration_verified': False}
    if not args.scene_only and not args.offline:
        review = json.loads((OUT / 'native-visual-review.json').read_text())
        assert review['decision'] == 'accept' and review['scene_sha256'] == result['after_scene_sha256']
        assert {r['view'] for r in review['images']} == {'hedge-low', 'east-hedge-low', 'low-border', 'raised-bed'}
        for row in review['images']:
            p = ROOT / row['image']
            assert sha(p) == row['sha256']
            metadata = json.loads(p.with_name(p.stem + '-camera.json').read_text())
            assert all(metadata['Restoration'].values())
            assert metadata['Capture']['SourceSceneSha256'] == result['after_scene_sha256']
        result.update(native_visual_review_verified=True, capture_restoration_verified=True)
    (OUT / ('offline-scene-check.json' if args.offline else 'scene-check.json' if args.scene_only else 'verification.json')).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
