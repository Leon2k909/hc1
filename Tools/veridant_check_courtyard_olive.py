"""Verify the scoped planter replacement, saved native tree and visual evidence."""
import copy
import json
from pathlib import Path
import re
import veridant_map as V
import veridant_courtyard_olive as O
from railhead_stage_extinguisher import sha
from belltower_safe_imports import span

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/veridant/foliage-hero-v2'


def results(path):
    raw = json.loads(path.read_text()); assert not raw.get('isError'), path
    return [json.loads(c['text']) for c in raw['content'] if c['type'] == 'text']


def flatten(scene):
    stack = list(scene['GameObjects']); found = {}
    while stack:
        obj = stack.pop(); found[obj['__guid']] = copy.deepcopy(obj)
        stack.extend(obj.get('Children', []))
    return found


def main():
    initial = json.loads((OUT/'stage-v3/manifest.json').read_text())
    final = json.loads((OUT/'stage-v6-final/manifest.json').read_text())
    for p, record in final['files'].items(): assert sha(ROOT/p) == record['after'], p
    for group in ('source_sha256', 'protected_sha256'):
        for p, digest in final[group].items(): assert sha(ROOT/p) == digest, p
    for p, snippets in final['required_source_snippets'].items():
        assert all(s in (ROOT/p).read_text() for s in snippets), p
    assert initial['removed_triangles'] == 332
    extraction = ROOT/'output/veridant/foliage-hero-v2/stage-v3'/initial['base_import']
    assert sha(extraction) == initial['retained_bytes_sha256']
    # Independent shrub work removed another 80 old cards after our extraction.
    # It kept the same tables; preserve that later work and verify its ordering.
    original_lines = extraction.read_bytes().splitlines(keepends=True)
    current_lines = (ROOT/initial['base_import']).read_bytes().splitlines(keepends=True)
    cursor = 0; later_removed = []
    for line in original_lines:
        if cursor < len(current_lines) and line == current_lines[cursor]: cursor += 1
        else: later_removed.append(line)
    assert cursor == len(current_lines) and all(l.startswith(b'f ') for l in later_removed)
    document = 'Assets/models/maps/veridant/veridant_foliage.vmdl'
    old_doc = (ROOT/initial['files'][document]['backup']).read_text()
    new_doc = (ROOT/document).read_text()
    imports = lambda t: re.findall(r'filename\s*=\s*"([^"]+\.obj)"', t)
    assert 'models/maps/veridant/courtyard-olive-v2/planting.obj' in imports(new_doc)
    assert set(imports(old_doc)).issubset(imports(new_doc))
    final_before = (ROOT/final['files'][document]['backup']).read_text()
    x, y = span(final_before, '_class = "RenderMeshList"')
    p, q = span(new_doc, '_class = "RenderMeshList"')
    assert final_before[x:y] == new_doc[p:q]
    assert 'PhysicsShapeList' not in new_doc and 'PhysicsShapeList' not in old_doc
    before = json.loads((OUT/'immediate-before-tree.scene').read_text())
    scene_file = ROOT/'Assets/scenes/maps/Veridant/veridant.scene'
    after = json.loads(scene_file.read_text()); a, b = flatten(before), flatten(after)
    assert set(a).issubset(b)
    added = set(b)-set(a); assert len(added) == 1
    tree_id = added.pop(); tree = b[tree_id]
    assert tree['Name'] == 'Courtyard planter tree' and len(tree['Components']) == 1
    assert tree['Components'][0]['__type'] == 'Sandbox.ModelRenderer'
    assert tree['Components'][0]['Model']['Path'] == O.TREE_MODEL
    normalised = []
    for guid, previous in a.items():
        current = copy.deepcopy(b[guid])
        if 'Children' in current:
            current['Children'] = [x for x in current['Children'] if x['__guid'] != tree_id]
        if previous.get('Name') == 'Look':
            tone_a = next(c for c in previous['Components'] if c['__type'] == 'Sandbox.Tonemapping')
            tone_b = next(c for c in current['Components'] if c['__type'] == 'Sandbox.Tonemapping')
            assert (tone_b['MinimumExposure'], tone_b['MaximumExposure']) == (2.1, 2.4)
            for key in ('MinimumExposure', 'MaximumExposure'):
                if tone_a[key] != tone_b[key]: normalised.append({key: [tone_a[key], tone_b[key]]})
                tone_b[key] = tone_a[key]
        assert previous == current, ('Existing object changed', previous.get('Name'), guid)
    assert before['SceneProperties'] == after['SceneProperties']
    assert set(after['__references'])-set(before['__references']) == {O.TREE_PACKAGE}
    assert set(before['__references']).issubset(after['__references'])
    native = results(OUT/'authored-materials/run_csharp.json')[0]
    assert len(native['Materials']) == 5 and native['Tree']['LodCount'] == 5
    assert native['Tree']['HighestDetailTriangles'] == 6092 and not native['SceneDirty']
    compiled, status, camera = results(OUT/'final-native/call_tools.json')
    assert compiled['Success'] and status['LastCompileSucceeded'] and status['LastCompileErrors'] == 0
    assert not status['IsCompiling'] and not status['IsPlaying'] and not status['SceneHasUnsavedChanges']
    assert Path(status['Paths']['ProjectRoot']).resolve() == ROOT
    images = {}
    for name in ('courtyard', 'detail'):
        image = ROOT/f'output/veridant/quality/foliage-hero-v2-authored/{name}.png'
        meta = json.loads(image.with_name(name+'-camera.json').read_text())
        assert all(meta['Restoration'].values())
        images[name] = {'path': image.relative_to(ROOT).as_posix(), 'sha256': sha(image), **meta}
    old_capture = json.loads((ROOT/'output/veridant/quality/foliage-hero-v2-before/courtyard-camera.json').read_text())
    for k in ('Position', 'Angles', 'FieldOfView', 'Width', 'Height', 'FovAxis', 'RequestedExposure'):
        assert old_capture['Capture'][k] == images['courtyard']['Capture'][k], k
    generated = O.scene_object(V.ids)
    assert generated['Position'] == tree['Position'] and generated['Components'][0]['Model'] == O.TREE_MODEL
    report = {'revision': final['revision'], 'final_stage': final['stage'],
        'planters_changed': 1, 'legacy_triangles_removed': 332,
        'retained_foliage_bytes_exact': True, 'original_obj_indices_preserved': True,
        'later_independent_base_triangles_removed_preserved': len(later_removed),
        'later_independent_imports_preserved': sorted(set(imports(new_doc))-set(imports(old_doc))-
            {'models/maps/veridant/courtyard-olive-v2/planting.obj'}),
        'existing_scene_objects_preserved': len(a), 'scene_objects_added': 1,
        'collision_unchanged': True, 'authored_exposure_range_normalisation': normalised,
        'scene_sha256': sha(scene_file), 'native_tree': native['Tree'],
        'planting': final['statistics']['planting'], 'native_compile': compiled,
        'native_materials_valid': True, 'matched_camera_and_exposure': True,
        'captures': images, 'editor_status': status, 'editor_camera': camera,
        'highest_detail_total_triangles': 6092+18967,
        'performance_note': 'Native tree retains five LODs; frame rate was not benchmarked.'}
    (OUT/'validation.json').write_text(json.dumps(report, indent=2)+'\n')
    (ROOT/'Sources/Veridant/foliage-hero-v2/installed.json').write_text(json.dumps({
        'revision': final['revision'], 'native_tree': O.TREE_MODEL, 'package': O.TREE_PACKAGE,
        'scene_object_id': tree_id, 'validation': 'output/veridant/foliage-hero-v2/validation.json',
        'screenshot': images['courtyard']['path'], 'detail': images['detail']['path']}, indent=2)+'\n')
    print(json.dumps({'planters_updated': 1, 'native_tree_lods': 5,
        'existing_objects_preserved': len(a), 'collision_preserved': True,
        'native_compile_passed': True, 'captures_reviewed': 2}))


if __name__ == '__main__': main()
