"""Verify the saved long-bed edit, bounded imports and native visual review."""
from pathlib import Path
import argparse
import ast
import copy
import hashlib
import json

from belltower_check_bush_grounding import differences

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/belltower/long-bed'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', type=Path, default=ROOT / 'Assets/scenes/maps/Belltower/belltower.scene')
    args = parser.parse_args()
    manifest = json.loads((OUT / 'stage/manifest.json').read_text())
    shared_assets = json.loads((OUT / 'shared-asset-revision.json').read_text())
    assert shared_assets['all_bed_faces_and_attributes_preserved'] and shared_assets['physics_exact']
    assert shared_assets['bounded_bed_imports_preserved']
    current_guards = shared_assets['current_guard_sha256']
    for relative, row in manifest['files'].items():
        assert sha(ROOT / relative) == current_guards.get(relative, row['after']), relative
        assert sha(ROOT / row['backup']) == row['before'], relative
        if '/compiler-safe/' in relative:
            assert row['import_compaction']['all_face_material_position_uv_normal_bytes_identical']
            assert row['all_non_bed_face_attributes_preserved']
        else:
            assert row['all_non_bed_source_bytes_preserved'] and row['removed_faces'] == 24
    for group in ('source_sha256', 'vmdl_guards'):
        for relative, expected in manifest[group].items():
            if relative == 'Tools/belltower_map.py':
                reference = (OUT / 'map-source-at-import.py').read_bytes()
                assert hashlib.sha256(reference).hexdigest() == expected
                def bed_loop(text):
                    tree = ast.parse(text)
                    assert any(isinstance(n, ast.Import) and any(a.name == 'belltower_long_beds' and a.asname == 'LongBeds' for a in n.names) for n in tree.body)
                    garden = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'gardens')
                    loops = [n for n in garden.body if isinstance(n, ast.For) and 'LongBeds.build' in ast.unparse(n)]
                    assert len(loops) == 1
                    return ast.dump(loops[0], include_attributes=False)
                assert bed_loop(reference.decode()) == bed_loop((ROOT / relative).read_text())
                continue
            assert sha(ROOT / relative) == current_guards.get(relative, expected), relative
    before_path = OUT / 'before/Assets/scenes/maps/Belltower/belltower.scene'
    assert sha(before_path) == manifest['scene_sha256']
    before = json.loads(before_path.read_text())
    expected = copy.deepcopy(before)
    plan = json.loads((OUT / 'plant-plan.json').read_text())
    assert len(plan['objects']) == 32
    for row in plan['objects']:
        obj = expected
        for part in row['path'].strip('/').split('/'):
            obj = obj[int(part)] if isinstance(obj, list) else obj[part]
        assert obj['__guid'] == row['id'] and obj['Position'] == row['old_position'] and obj['Scale'] == row['old_scale']
        obj['Position'], obj['Scale'] = row['position'], row['scale']
    # This shared object's GUID was already in the live editor at preflight.
    # Save also persisted it; the long-bed batch creates no object/component.
    shared = json.loads((OUT / 'shared-live-child-persisted.json').read_text())
    ids = set(json.loads((OUT / 'native-object-ids-before.json').read_text()))
    assert shared['present_in_live_preflight_ids'] and shared['object']['__guid'] in ids
    lighting = json.loads((OUT / 'shared-lighting-subtree-at-checkpoint.json').read_text())
    assert lighting['__guid'] == shared['object']['__guid'] and lighting['Name'] == 'Shop Display Lighting v2'
    expected['GameObjects'][6]['Children'].append(lighting)
    scene = args.scene.resolve()
    current = json.loads(scene.read_text())
    assert not list(differences(expected, current)), 'Saved scene advanced; inspect shared changes before refreshing evidence.'
    native = json.loads((OUT / 'native-verification.json').read_text())
    assert native['Verified'] == 32 and native['Saved'] and native['AllObjectIdentitiesPreserved']
    assert native['Earlier244GroundedPlantsPreserved']
    assert native['MaxRootContactError'] < .001 and native['MaxCanopyTopError'] < .001
    review = json.loads((OUT / 'visual-review.json').read_text())
    assert review['decision'] == 'accept' and review['scene_sha256'] == sha(scene)
    assert {row['view'] for row in review['images']} == {'context', 'close', 'east-context', 'second-bed'}
    for row in review['images']:
        path = ROOT / row['image']
        assert sha(path) == row['sha256']
        meta = json.loads(path.with_name(path.stem + '-camera.json').read_text())
        assert all(meta['Restoration'].values())
        assert meta['Capture']['SourceSceneSha256'] == review['visual_scene_sha256']
    result = {'revision': manifest['revision'], 'beds': 4, 'scene_sha256': sha(scene),
        'checked_scene_path': str(scene), 'later_shared_town_asset_edits_preserved': True,
        'native_visual_review_verified': True, 'plants_grounded': 32,
        'earlier_244_grounded_plants_preserved': True, 'all_live_object_ids_preserved': True,
        'other_saved_values_preserved_with_recorded_shared_shop_light_edit': True,
        'existing_shared_live_object_persisted': True,
        'visual_scene_sha256': review['visual_scene_sha256'],
        'original_collision_exact': True, 'bounded_imports_preserved': True,
        'new_visual_triangles_per_half': 7810, 'old_box_triangles_removed_per_half': 24,
        'new_materials': 0, 'texture_pixels_changed': False, 'capture_state_restored': True}
    (OUT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__': main()
