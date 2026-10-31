"""Install only the approved pump and revision-4 finish without starting the editor."""
import os
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
import psutil
process = psutil.Process()
process.nice(psutil.IDLE_PRIORITY_CLASS)
process.cpu_affinity(process.cpu_affinity()[-2:])
from collections import Counter
from pathlib import Path
import hashlib
import json
import re
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OUT = ROOT / 'output/collider-pump-skid-accepted-20261030'
TRIAL = ROOT / 'Assets/models/props/collider/pump-skid-trial-v1'
sys.path.insert(0, str(ROOT / 'Tools'))
import collider_pump_skid as PS
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def key(paint, points):
    return paint, tuple(sorted(tuple(round(float(v), 3) for v in p) for p in points))


def triangles(path, local=False):
    positions, paint = [], ''
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a, z, n = map(float, line.split()[1:])
            positions.append(np.array((-a, n, z)) + (PS.ORIGIN if local else 0))
        elif line.startswith('usemtl '):
            paint = line[7:]
        elif line.startswith('f '):
            yield key(paint, [positions[int(t.split('/')[0]) - 1] for t in line.split()[1:]])


def main():
    assert not (OUT / 'installed.json').exists(), 'Pump already installed'
    candidate = json.loads((HERE / 'candidate.json').read_text())
    review = json.loads((HERE / 'review.json').read_text())
    assert review['realismRevision'] == 4 and review['status'] == 'preview-ready-awaiting-user-approval'
    assert candidate['models']['after']['meshSHA256'] == '7470b3f2288165c8eabfcd0ad5490400e4139be11a6d26d4ad86437a24fe4c81'
    for rel, expected in review['proposalSourceSHA256'].items():
        assert sha(ROOT / rel) == expected, rel
    for rel, expected in candidate['protectedSourceSHA256'].items():
        assert sha(ROOT / rel) == expected, rel
    relative = Path('models/maps/collider/collider_detail.obj')
    source = ROOT / 'Assets' / relative
    lines = source.read_bytes().decode('utf-8').splitlines(keepends=True)
    positions, paint, kept, removed = [], '', [], []
    remaining = Counter(triangles(TRIAL / 'before.obj', local=True))
    assert sum(remaining.values()) == 2420
    for number, line in enumerate(lines, 1):
        if line.startswith('v '):
            a, z, n = map(float, line.split()[1:])
            positions.append(np.array((-a, n, z)))
        elif line.startswith('usemtl '):
            paint = line.split()[1]
        elif line.startswith('f '):
            signature = key(paint, [positions[int(t.split('/')[0]) - 1] for t in line.split()[1:]])
            if remaining[signature]:
                remaining[signature] -= 1
                removed.append(number)
                continue
        kept.append(line)
    assert not +remaining and len(removed) == 2420
    offsets = tuple(sum(line.startswith(p) for line in lines) for p in ('v ', 'vt ', 'vn '))
    extra = ['\n# Approved pump skid at plan (-850,-350,0); original physics retained\n',
             'o collider_approved_pump_skid\n']
    for line in (TRIAL / 'after.obj').read_text().splitlines(keepends=True):
        if line.startswith(('#', 'mtllib ', 'o ')):
            continue
        if line.startswith('v '):
            a, z, n = map(float, line.split()[1:])
            e, north, height = PS.ORIGIN + np.array((-a, n, z))
            line = f'v {-e:.3f} {height:.3f} {north:.3f}\n'
        elif line.startswith('f '):
            line = 'f ' + ' '.join('/'.join(str(int(v) + offsets[i]) for i, v in enumerate(t.split('/')))
                                     for t in line.split()[1:]) + '\n'
        extra.append(line)
    count = sum(line.startswith('f ') for line in lines)
    after_count = sum(line.startswith('f ') for line in kept + extra)
    assert after_count == count - 2420 + 58005
    remaps = dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}', (TRIAL / 'after.vmdl').read_text()))
    assert len(remaps) == 25 and all(p.startswith('ps_') for p in remaps)
    old_doc = source.with_suffix('.vmdl').read_bytes().decode('utf-8')
    assert not any(p in old_doc for p in remaps)
    additions = ',\n'.join(f'\t\t\t\t\t\t\t{{ from = "{p}" to = "{path}" }}' for p, path in sorted(remaps.items()))
    pattern = r'(\bremaps\s*=\s*\[)([\s\S]*?)(\n\t{6}\])'
    new_doc, replacements = re.subn(pattern, lambda m: m[1] + m[2].rstrip().rstrip(',') + ',\n' + additions + m[3], old_doc, count=1)
    assert replacements == 1
    marker = 'PhysicsShapeList'
    assert old_doc[old_doc.index(marker):] == new_doc[new_doc.index(marker):]
    old_mtl = source.with_suffix('.mtl').read_bytes().decode('utf-8')
    payloads = {
        relative: ''.join(kept + extra),
        relative.with_suffix('.mtl'): old_mtl + ''.join(f'newmtl {p[:-5]}\nKd 1 1 1\nd 1\n' for p in sorted(remaps)),
        relative.with_suffix('.vmdl'): new_doc,
    }
    generator = ROOT / 'Tools/collider_map.py'
    old_generator = generator.read_bytes()
    updated = old_generator.decode('utf-8')
    changes = [
        ('import collider_column_base as CB\n', 'import collider_column_base as CB\nimport collider_pump_skid as PS\n'),
        ("        if paint.startswith('cb_'):", "        if paint.startswith('ps_'):\n            m.material_overrides[paint] = f'{PS.MATERIAL_DIR}/{paint}.vmat'\n            m.tile_overrides[paint] = 12.\n        elif paint.startswith('cb_'):"),
        ('def hardcase(m,e,n,z=0,w=78,d=46,h=55,heading=0):\n',
         'def hardcase(m,e,n,z=0,w=78,d=46,h=55,heading=0):\n'
         '    if (e,n,z,w,d,h,heading)==(-850,-350,0,106,58,74,0):\n'
         '        frame=B.Frame(e,n,heading,z)\n'
         '        frame.box(m,-w/2,w/2,-d/2,d/2,3,h,None,surface="plastic")\n'
         '        PS.append(m)\n'
         '        return\n'),
    ]
    for old, new in changes:
        assert updated.count(old) == 1, old
        updated = updated.replace(old, new)
    compile(updated, str(generator), 'exec')
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for rel, payload in payloads.items():
        target, backup, stage = ROOT / 'Assets' / rel, OUT / 'before' / rel, OUT / 'stage' / rel
        backup.parent.mkdir(parents=True, exist_ok=True)
        stage.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(target.read_bytes())
        stage.write_bytes(payload.encode('utf-8'))
        records.append({'relative': rel.as_posix(), 'before': sha(target), 'after': sha(stage)})
    backup = OUT / 'before/Tools/collider_map.py'
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_bytes(old_generator)
    completed = []
    try:
        assert generator.read_bytes() == old_generator
        generator.write_bytes(updated.encode('utf-8'))
        for record in records:
            rel = Path(record['relative'])
            target = ROOT / 'Assets' / rel
            assert sha(target) == record['before'], str(rel)
            incoming = target.with_name(target.name + '.pump-skid-incoming')
            with incoming.open('wb') as stream:
                stream.write((OUT / 'stage' / rel).read_bytes())
                stream.flush()
                os.fsync(stream.fileno())
            incoming.replace(target)
            assert sha(target) == record['after'], str(rel)
            completed.append(rel)
        changed = {'Assets/' + r['relative'] for r in records} | {'Tools/collider_map.py'}
        protected = {p: h for p, h in candidate['protectedSourceSHA256'].items() if p not in changed}
        for rel, expected in protected.items():
            assert sha(ROOT / rel) == expected, rel
    except Exception:
        generator.write_bytes(old_generator)
        for rel in completed:
            (ROOT / 'Assets' / rel).write_bytes((OUT / 'before' / rel).read_bytes())
        raise
    # Retain the original review resources for rollback outside the live asset tree.
    retired = []
    for old in sorted(TRIAL.glob('before.*')):
        backup = OUT / 'retired-before-resources' / old.name
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(old.read_bytes())
        assert sha(old) == sha(backup)
        old.unlink()
        retired.append(old.relative_to(ROOT).as_posix())
    synced, preserved = [], []
    for record in records:
        rel = Path(record['relative'])
        primary = ROOT / 'output/collider/stage/assets' / rel
        if primary.exists() and sha(primary) == record['before']:
            primary.write_bytes((ROOT / 'Assets' / rel).read_bytes())
            synced.append(rel.as_posix())
        else:
            preserved.append(rel.as_posix())
    result = {
        'status': 'accepted-installed-in-map-sources', 'userApproved': True,
        'approvedSurfaceRevision': 4, 'editorUsed': False, 'engineCompilation': 'pending',
        'placementPlan': PS.ORIGIN.tolist(), 'removedOldTriangles': 2420, 'addedApprovedTriangles': 58005,
        'detailTrianglesBefore': count, 'detailTrianglesAfter': after_count,
        'files': records, 'removedFaceLines': removed, 'protectedOtherFiles': protected,
        'sceneAndPhysicsUnchanged': True, 'retiredOldStandaloneResources': retired,
        'generatorFile': {'path': 'Tools/collider_map.py', 'before': hashlib.sha256(old_generator).hexdigest(), 'after': sha(generator)},
        'sourceGeneratorHook': 'Tools/collider_pump_skid.py; collider_map.hardcase exact selected placement',
        'helperSHA256': sha(ROOT / 'Tools/collider_pump_skid.py'),
        'primaryStageSynchronized': synced, 'newerStagedFilesPreserved': preserved,
        'approvedProposalSources': {p: h for p, h in review['proposalSourceSHA256'].items() if Path(p).stem != 'before'},
    }
    for p in (OUT / 'installed.json', HERE / 'installed.json'):
        p.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('removedFaceLines', 'protectedOtherFiles', 'approvedProposalSources')}))


if __name__ == '__main__':
    main()
