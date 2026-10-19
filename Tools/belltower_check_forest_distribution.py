"""Check the exported native model sources against the accepted woodland."""
import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'output/belltower/quality/forest-distribution-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mesh(path):
    vertices, texcoords, texture_faces, indices = [], [], [], []
    for line in path.read_text(encoding='utf-8').splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == 'v':
            vertices.append(list(map(float, fields[1:])))
        elif fields[0] == 'vt':
            texcoords.append(list(map(float, fields[1:])))
        elif fields[0] == 'f':
            face = [tuple(map(int, token.split('/'))) for token in fields[1:]]
            assert len(face) == 3 and all(normal == 1 for _, _, normal in face)
            texture_faces.append([texture for _, texture, _ in face])
            indices.append([index - 1 for index, _, _ in face])
    vertices, texcoords, texture_faces, indices = map(np.asarray, (vertices, texcoords, texture_faces, indices))
    assert np.isfinite(vertices).all() and np.isfinite(texcoords).all()
    assert vertices.shape[0] % 4 == 0 and indices.shape == (vertices.shape[0] // 2, 3)
    assert indices.min() == 0 and indices.max() == len(vertices) - 1
    triangles = vertices[indices]
    assert np.all(np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1) > 1)
    assert texture_faces.min() >= 1 and texture_faces.max() <= len(texcoords)
    return vertices.reshape(-1, 4, 3), texcoords, texture_faces.reshape(-1, 2, 3)


def main():
    manifest_path = STAGE / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    for path, expected in manifest['source_sha256'].items():
        assert sha(ROOT / path) == expected, path
    for item in manifest['files']:
        assert sha(ROOT / item['source']) == sha(ROOT / 'Assets' / item['path']) == item['sha256']
    crowns = np.load(ROOT / 'output/belltower/quality/parcel-v4-forest/crowns.npy')
    selected = np.load(STAGE / 'selected-indices.npy')
    retained = np.load(STAGE / 'retained-indices.npy')
    assert len(np.unique(selected)) == len(selected) == manifest['original_cards']
    assert len(np.unique(retained)) == len(retained) == manifest['candidate_cards']
    assert np.isin(retained, selected).all()
    sector_ids = np.floor(crowns[:, :2] / 12000).astype(int)
    counts = []
    for item, count in zip(manifest['model_overrides'], manifest['sectors']):
        ids = np.flatnonzero(np.all(sector_ids == count['sector'], axis=1))
        keep = np.isin(ids, retained)
        original = (ROOT / 'Assets' / item['original']).with_suffix('.obj')
        control = (ROOT / 'Assets' / item['control']).with_suffix('.obj')
        candidate = (ROOT / 'Assets' / item['clumped']).with_suffix('.obj')
        assert sha(original) == sha(control), original
        before, uv, textures = mesh(control)
        after, trial_uv, trial_textures = mesh(candidate)
        assert before.shape[0] == len(ids) == count['original']
        assert after.shape[0] == keep.sum() == count['candidate']
        assert np.array_equal(after, before[keep]), 'Exported retained card positions/heights/sizes changed'
        assert np.array_equal(uv, trial_uv) and np.array_equal(trial_textures, textures[keep]), 'Exported atlas selection changed'
        for variant in ('control', 'clumped'):
            text = (ROOT / 'Assets' / item[variant]).read_text()
            assert 'PhysicsShape' not in text and 'PhysicsHull' not in text
        counts.append(dict(sector=count['sector'], original_cards=len(before), candidate_cards=len(after), exact_exported_subset=True))
    compilers = []
    for index in range(16):
        result = json.loads((STAGE / f'compile-{index}/asset_compile.json').read_text())['structuredContent']
        assert result['Success']
        path = ROOT / 'Assets' / result['Path']
        compilers.append(dict(path=result['Path'], compiled_sha256=sha(Path(str(path) + '_c'))))
    result = dict(passed=True, manifest_sha256=sha(manifest_path), checker_sha256=sha(Path(__file__)),
                  sector_counts=counts, native_model_compilation=compilers,
                  original_cards=len(selected), candidate_cards=len(retained), removed_cards=len(selected) - len(retained),
                  exported_controls_exact=True, exported_candidate_is_exact_subset=True,
                  source_atlas_and_shader_unchanged=True, authored_physics_shapes=0,
                  scope='Exported source topology, retained-card data and native model compilation. Does not prove native appearance, culling or gameplay performance.',
                  native_visual_verified=False, accepted_assets_changed=False)
    (STAGE / 'geometry-checks.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('passed', 'original_cards', 'candidate_cards', 'removed_cards', 'exported_controls_exact', 'native_visual_verified')}))


if __name__ == '__main__':
    main()
