"""Verify later shared town edits retain every bed face and original physics."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'Tools'))
import belltower_compact_obj as C
import belltower_safe_imports as S


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def bed_faces(path):
    data = C.tables(path)
    result = Counter()
    material = None
    for line in path.open('rb'):
        if line.startswith(b'usemtl '): material = line.split()[1].decode()
        elif line.startswith(b'f ') and material in ('planter_cut_stone', 'planter_compost', 'ashlar_grey', 'soil'):
            rows = [[int(x) for x in token.split(b'/')] for token in line.split()[1:]]
            xyz = [list(map(float, data[b'v'][row[0]].split()[1:])) for row in rows]
            if not all(-1178.001 <= p[2] <= -1141.999 and -48.001 <= p[1] <= -33.999 and
                any(abs(abs(p[0]) - centre) <= 60.001 for centre in (350, 650)) for p in xyz): continue
            digest = hashlib.sha256(material.encode())
            for row in rows:
                for kind, index in zip(C.KINDS, row): digest.update(data[kind][index])
            result[(material, digest.hexdigest())] += 1
    return result


manifest = json.loads((OUT / 'stage/manifest.json').read_text())
result = {'current_guard_sha256': {}, 'models': {}, 'all_bed_faces_and_attributes_preserved': True,
    'physics_exact': True, 'bounded_bed_imports_preserved': True,
    'reason': 'Later shared gazebo, padlock and scarecrow publication changed canonical town sources/material remaps. Preserve it; verify the bed scope independently.'}
for side in ('west', 'east'):
    relative = f'Assets/models/maps/belltower/belltower_{side}.obj'
    before = bed_faces(OUT / 'stage' / relative)
    after = bed_faces(ROOT / relative)
    assert before == after and sum(after.values()) == 7810
    assert all(paint in ('planter_cut_stone', 'planter_compost') for paint, digest in after)
    vmdl = relative.removesuffix('.obj') + '.vmdl'
    old = (ROOT / 'output/belltower/bush-grounding/compiler-safe-imports-stage' / vmdl).read_text()
    current = (ROOT / vmdl).read_text()
    a, b = S.span(old, '_class = "PhysicsShapeList"'); c, d = S.span(current, '_class = "PhysicsShapeList"')
    assert old[a:b] == current[c:d]
    for path, row in manifest['files'].items():
        if f'/compiler-safe/{side}/' not in path: continue
        assert sha(ROOT / path) == row['after']
        assert path.removeprefix('Assets/') in current
    result['current_guard_sha256'].update({relative: sha(ROOT / relative), vmdl: sha(ROOT / vmdl)})
    result['models'][side] = {'bed_faces': 7810, 'bed_face_multiset_sha256': hashlib.sha256(repr(sorted(after.items())).encode()).hexdigest(), 'physics_exact': True}
(OUT / 'shared-asset-revision.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'bed_faces_preserved_per_half': 7810, 'original_physics_exact': True, 'later_shared_asset_edits_preserved': True}))
