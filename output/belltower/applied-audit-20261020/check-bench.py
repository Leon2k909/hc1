"""Read-only check that the current town render imports contain the revised benches."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Tools'))
import belltower_map as B
import map_kit as K

OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def faces(path, wanted=None):
    vertices = [None]
    material = None
    result = Counter()
    before = sha(path)
    with path.open('rb') as stream:
        for line in stream:
            if line.startswith(b'v '):
                vertices.append(line[2:].strip())
            elif line.startswith(b'usemtl '):
                material = line.split()[1]
            elif line.startswith(b'f '):
                key = (material, frozenset(vertices[int(t.split(b'/')[0])] for t in line.split()[1:]))
                if wanted is None or key in wanted:
                    result[key] += 1
    assert sha(path) == before, f'Asset changed during read: {path}'
    return result


placements = [((-190, -820), -90, 50, 0)]
placements += [((e, -965), 0, 80, 0) for e in (-1640, -1340, -820, -420)]
placements += [((-500, -1160), 0, 60, B.GARDEN_Z)]
placements += [(centre, yaw, 70, 0) for yaw, centre in ((90, (-150, 130)), (45, (-110, 240)), (135, (-110, 20)))]
model = K.Model()
for centre, yaw, length, z in placements:
    B.bench(model, centre, yaw, length, z)

rows = []
for side in ('west', 'east'):
    expected = Counter()
    current_model = model if side == 'west' else model.mirrored()
    for paint, polygons in current_model.polygons.items():
        for points, _ in polygons:
            vertices = [K.obj_vector(K.to_world(p)).encode() for p in points]
            for i in range(1, len(vertices) - 1):
                expected[(paint.encode(), frozenset((vertices[0], vertices[i], vertices[i + 1])))] += 1
    vmdl = ROOT / f'Assets/models/maps/belltower/belltower_{side}.vmdl'
    sources = [p for p in re.findall(r'filename\s*=\s*"([^"]+\.obj)"', vmdl.read_text())
               if re.search(r'_(?:furniture_wood(?:_dark)?|iron_black)\.obj$', p)]
    found = Counter()
    hashes = {}
    for relative in sources:
        path = ROOT / 'Assets' / relative
        found.update(faces(path, expected))
        hashes[relative] = sha(path)
    missing = expected - found
    row = {'side': side, 'benches': len(placements), 'expected_triangles': sum(expected.values()),
           'missing_triangles': sum(missing.values()), 'all_revised_bench_geometry_present': not missing,
           'scope': 'Material and exported triangle positions, including arms, grips, slats, feet and bolts.',
           'referenced_imports_sha256': hashes, 'vmdl_sha256': sha(vmdl)}
    rows.append(row)
    assert not missing, row

report = {'canonical_project': str(ROOT), 'benches_verified': len(placements) * 2,
          'read_only_asset_check': True, 'scene_or_assets_edited': False, 'models': rows}
(OUT / 'bench-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'benches_verified': report['benches_verified'], 'models': [
    {k: v for k, v in row.items() if k not in ('referenced_imports_sha256', 'vmdl_sha256', 'scope')} for row in rows]}))
