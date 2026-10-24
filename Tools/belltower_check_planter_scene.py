"""Audit the native planter save, including the engine's explicit serialization updates."""
import collections
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'output/belltower/quality/oct20-continuation'
SCENE = ROOT / 'Assets/scenes/maps/Belltower/belltower.scene'
PROOF = ROOT / 'output/belltower/planter-v2/scene-revision.json'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def audit():
    plan = json.loads((EVIDENCE / 'planter-position-plan.json').read_text())
    original = ROOT / plan['before_path']
    assert sha(original) == plan['before_scene_sha256']
    before = json.loads(original.read_text())
    after = json.loads(SCENE.read_text())
    expected = {r['json_path']: (r['old'], r['new']) for r in plan['objects']}
    assert len(expected) == 6
    authored = []
    normalization = collections.Counter()
    # These five entries are generated prefab instance bookkeeping, not authored
    # overrides. Keep the exact observed deltas; do not permit arbitrary map edits.
    bindings = {
        '/GameObjects/20/__PrefabIdToInstanceId': {
            'removed': {'7313a516-7687-4997-8cfb-0aae4f61d12a': '54f8e587-d1b0-8b44-ae8a-4ba71ac6ddd4'},
            'added': {'fc98b206-8a8c-4d62-9268-7890d25a5409': '4dd32d0d-82a4-8eff-9f2e-7e16f59a5f9a'}},
        '/GameObjects/21/__PrefabIdToInstanceId': {
            'removed': {'3f91be8e-8abc-480a-b929-7bec0ba8be3c': '6f4201c1-4791-8958-ae0a-476621da2adc'},
            'added': {'6330b2e1-f401-4f2e-a683-c4f6dff1ef53': 'ae05a707-bd2c-81ce-b4d0-0c4ec07b932b'}},
        '/GameObjects/22/__PrefabIdToInstanceId': {
            'removed': {},
            'added': {'37b4fba5-67ef-81bb-866f-c8cfc5b5a492': 'aad6bf84-e453-885e-a25f-78d83db2b3bf'}}}
    defaults = {k: None for k in ('LodOverride', 'MaterialGroup', 'MaterialOverride', 'Materials',
        'OnComponentDestroy', 'OnComponentDisabled', 'OnComponentEnabled', 'OnComponentFixedUpdate',
        'OnComponentStart', 'OnComponentUpdate')}
    defaults.update(BodyGroups=18446744073709551615,
        RenderOptions={'GameLayer': True, 'OverlayLayer': False, 'BloomLayer': False, 'AfterUILayer': False})

    def compare(a, b, path=''):
        if a == b:
            return
        if path in expected:
            assert (a, b) == expected[path], (path, a, b)
            av, bv = map(lambda s: list(map(float, s.split(','))), (a, b))
            assert av[:2] == bv[:2] and abs(bv[2] - av[2] + 8) < 1e-6
            authored.append(path)
            return
        if path in bindings:
            delta = {'removed': {k: a[k] for k in a.keys() - b.keys()},
                     'added': {k: b[k] for k in b.keys() - a.keys()}}
            assert delta == bindings[path], (path, delta)
            assert all(a[k] == b[k] for k in a.keys() & b.keys())
            normalization['prefab_instance_binding_entries'] += sum(map(len, delta.values()))
            return
        if path.endswith('/Model') and isinstance(a, str) and isinstance(b, dict):
            assert set(b) == {'Id', 'Path'} and b['Path'] == a and b['Id']
            normalization['model_path_reference_expansion'] += 1
            return
        if isinstance(a, dict) and isinstance(b, dict):
            if set(a) == set(b) == {'Id', 'Path'}:
                assert a['Path'] == b['Path'] and a['Id'] and b['Id'], path
                normalization['resource_id_refresh_same_path'] += 1
                return
            missing = b.keys() - a.keys()
            if missing:
                assert a.get('__type') == b.get('__type') == 'Sandbox.ModelRenderer', path
                for key in missing:
                    assert key in defaults and b[key] == defaults[key], (path, key)
                    normalization['explicit_model_renderer_defaults'] += 1
            assert not a.keys() - b.keys(), path
            for key in a:
                compare(a[key], b[key], path + '/' + key)
            return
        if isinstance(a, list) and isinstance(b, list):
            assert len(a) == len(b), path
            for index, (x, y) in enumerate(zip(a, b)):
                compare(x, y, path + '/' + str(index))
            return
        if path.rsplit('/', 1)[-1] in ('Position', 'Rotation', 'Scale') and isinstance(a, str) and isinstance(b, str):
            av, bv = [float(x) for x in a.split(',')], [float(x) for x in b.split(',')]
            assert len(av) == len(bv)
            # Native vectors use single precision; textual digits and signed zero
            # may change without changing the represented transform.
            assert all(x == y or struct.unpack('f', struct.pack('f', x))[0] ==
                       struct.unpack('f', struct.pack('f', y))[0] for x, y in zip(av, bv)), (path, a, b)
            normalization['same_float32_transform_serialization'] += 1
            return
        raise AssertionError((path, a, b))

    compare(before, after)
    assert set(authored) == set(expected)
    prefabs = []
    for index in (20, 21, 22):
        old, new = before['GameObjects'][index], after['GameObjects'][index]
        assert old['__Prefab'] == new['__Prefab']
        assert old['__PrefabInstancePatch'] == new['__PrefabInstancePatch']
        resource = ROOT / 'Assets' / new['__Prefab']['Path']
        prefabs.append({'path': resource.relative_to(ROOT).as_posix(), 'current_source_sha256': sha(resource),
                        'authored_instance_patch_unchanged': True})
    return {'before_scene_sha256': sha(original), 'after_scene_sha256': sha(SCENE),
            'before_scene_snapshot': original.relative_to(ROOT).as_posix(),
            'plan': (EVIDENCE / 'planter-position-plan.json').relative_to(ROOT).as_posix(),
            'native_save_evidence': (EVIDENCE / 'lower-plants-and-save/call_tools.json').relative_to(ROOT).as_posix(),
            'authored_changes': plan['objects'], 'authored_positions_changed': 6,
            'delta_world_z': -8, 'all_other_authored_scene_data_preserved': True,
            'native_serialization_updates': dict(normalization), 'prefab_binding_deltas': bindings,
            'prefab_instance_patches': prefabs,
            'limitation': 'Native Save Scene refreshes generated prefab bindings; runtime game mode behaviour was not retested.'}


def verify(expected_before_sha):
    record = json.loads(PROOF.read_text())
    assert record['before_scene_sha256'] == expected_before_sha
    assert record == audit(), 'Scene revision audit changed'
    return record


if __name__ == '__main__':
    result = audit()
    PROOF.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: result[k] for k in ('after_scene_sha256', 'authored_positions_changed',
          'all_other_authored_scene_data_preserved', 'native_serialization_updates')}))
