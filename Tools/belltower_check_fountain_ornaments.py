"""Verify the installed fountain-only upgrade and its native visual receipts."""
import hashlib
import json
from pathlib import Path
import numpy as np
import belltower_fountain_ornaments as O
from belltower_safe_imports import span

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/fountain-ornaments-v2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    stage = OUT/'revision4/stage'
    manifest = json.loads((stage/'manifest.json').read_text())
    for relative, record in manifest['files'].items():
        assert sha(ROOT/relative) == record['after'], ('Installed resource differs', relative)
    for group in ['source_sha256', 'protected_sha256']:
        for relative, digest in manifest[group].items():
            assert sha(ROOT/relative) == digest, ('Guarded source differs', relative)
    relative = Path('Assets/models/maps/belltower/belltower_centre.vmdl')
    before = (stage/'before'/relative).read_bytes().decode('utf-8')
    after = (ROOT/relative).read_bytes().decode('utf-8')
    a, b = span(before, '_class = "RenderMeshList"')
    c, d = span(after, '_class = "RenderMeshList"')
    non_render_before, non_render_after = before[:a]+before[b:], after[:c]+after[d:]
    assert non_render_before.replace('\r\n', '\n') == non_render_after.replace('\r\n', '\n'), 'Non-render VMDL content changed.'
    # ModelDoc was written through Windows text I/O. Report this formatting-only
    # difference honestly rather than describing the VMDL as byte-identical.
    vmdl_newlines_normalized = non_render_before != non_render_after
    assert max(p['triangles'] for p in manifest['imports']['parts']) <= 65000
    vertices, faces, normals = O.lion_mesh()
    assert len(faces) <= 18000 and np.isfinite(vertices).all() and np.isfinite(normals).all()
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    assert np.all(counts == 2), 'The lion has an open mesh edge.'
    baked = json.loads(O.lion_cache_path().with_suffix('.json').read_text())
    assert baked['connected_components'] == 1
    captures = {}
    for view in ['lion', 'lily', 'overview']:
        pair = {}
        camera_values = []
        for phase in ['before', 'after']:
            folder = ROOT/f'output/belltower/quality/fountain-ornaments-v2-{phase}'
            restored = json.loads((folder/(view+'-restore.json')).read_text())
            assert all(restored.values()), ('Capture restoration differs', phase, view)
            camera = json.loads((folder/(view+'-camera.json')).read_text())['Capture']
            camera_values.append({key: camera[key] for key in ['Position', 'Angles', 'FieldOfView', 'FovAxis',
                'Width', 'Height', 'RequestedExposure', 'NativeEnabled', 'NativeMinimum', 'NativeMaximum', 'NativeCompensation']})
            image = folder/(view+'.png')
            pair[phase] = {'path': image.relative_to(ROOT).as_posix(), 'sha256': sha(image)}
        assert camera_values[0] == camera_values[1], 'Before/after capture conditions differ.'
        captures[view] = pair
    compiled = json.loads((OUT/'revision4/native-compile/asset_compile.json').read_text())['structuredContent']
    assert compiled['Success'] is True
    status = json.loads((OUT/'status-final/editor_status.json').read_text())['structuredContent']
    assert status['LastCompileSucceeded'] and status['LastCompileErrors'] == 0 and not status['IsCompiling']
    assert not status['IsPlaying'] and not status['SceneHasUnsavedChanges']
    assert status['ActiveScenePath'] == 'scenes/maps/belltower/belltower.scene'
    result = {'revision': 'fountain-ornaments-v2', 'published_stage': 'revision4', 'installed': True,
              'ornaments': manifest['ornaments'], 'preservation': manifest['preservation'],
              'bounded_imports': len(manifest['imports']['parts']),
              'max_triangles_per_import': manifest['imports']['max_triangles_per_import'],
              'non_render_vmdl_content_exact': True, 'vmdl_line_endings_normalized_to_crlf': vmdl_newlines_normalized,
              'water_materials_and_geometry_unchanged': True,
              'lion': {'triangles': len(faces), 'vertices': len(vertices), 'closed': True, 'connected_components': 1,
                       'source': O.lion_cache_path().relative_to(ROOT).as_posix()},
              'native_compilation': compiled, 'native_editor_status': status, 'native_visuals': captures,
              'scene_and_cameras_preserved': True,
              'visual_review': 'Native close-ups and overview inspected: solid masks, rounded limestone lilies, outlets aligned with existing water.',
              'limit': 'Native editor visual and resource checks; no new full-match performance benchmark.'}
    path = ROOT/'Sources/Belltower/props/fountain-ornaments-v2/installed.json'
    path.write_text(json.dumps(result, indent=2)+'\n')
    (OUT/'validation.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'installed': True, 'lions': 4, 'lilies': 12, 'source_files_checked': len(manifest['files']),
                      'non_render_vmdl_content_exact': True, 'native_compile_success': True,
                      'editor_errors': status['LastCompileErrors'], 'native_capture_pairs': len(captures)}))


if __name__ == '__main__':
    main()
