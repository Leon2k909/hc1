"""Verify the migration's exact scope and exported triangle attributes."""
from pathlib import Path
import hashlib
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'output/collider-wall-overlap-20261027'
manifest = json.loads((OUT/'stage/manifest.json').read_text())
relative = manifest['relative']
before = OUT/'stage/before'/relative
after = OUT/'stage/assets'/relative
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(before) == manifest['before'] and sha(after) == manifest['after']
old = before.read_text().splitlines(keepends=True)
new = after.read_text()
removed = {r['line'] for r in manifest['removedFaces']}
assert len(removed) == 20
prefix = ''.join(line for i,line in enumerate(old,1) if i not in removed)
assert new.startswith(prefix)
assert all(old[i-1].startswith('f ') for i in removed)
for path, expected in manifest['protected'].items():
    assert sha(ROOT/'Assets'/path) == expected, path
for path, expected in manifest['sources'].items():
    assert sha(ROOT/path) == expected, path
vertices,uvs,normals = [],[],[]
added = []
face_count = 0
for line in new.splitlines():
    if line.startswith('v '):
        vertices.append(np.array(list(map(float,line.split()[1:]))))
    elif line.startswith('vt '):
        uvs.append(np.array(list(map(float,line.split()[1:]))))
    elif line.startswith('vn '):
        normals.append(np.array(list(map(float,line.split()[1:]))))
    elif line.startswith('f '):
        face_count += 1
        if face_count > manifest['beforeTriangles']-len(removed):
            ids = [[int(v)-1 for v in token.split('/')] for token in line.split()[1:]]
            points = np.array([vertices[v] for v,t,n in ids])
            coords = np.array([uvs[t] for v,t,n in ids])
            normal = np.array([normals[n] for v,t,n in ids])
            assert np.isfinite(np.concatenate((points,normal,coords),axis=1)).all()
            cross = np.cross(points[1]-points[0],points[2]-points[0])
            area = np.linalg.norm(cross)*.5
            assert area > 1e-6
            assert all(np.dot(cross,n) > 0 for n in normal)
            added.append(area)
assert len(added) == manifest['addedTriangles'] == 31
assert face_count == manifest['afterTriangles']
audit = json.loads((OUT/'candidate-audit.json').read_text())
assert not audit['overlaps']
assert abs(manifest['removedArea'] - 648800.) < .001
result = {'success':True,'preservedOriginalAttributeTables':True,'preservedUnaffectedFaceLines':True,
    'beforeTriangles':manifest['beforeTriangles'],'removedTriangles':len(removed),'addedTriangles':len(added),
    'afterTriangles':face_count,'minimumAddedTriangleArea':min(added),'windingErrors':0,'degenerateTriangles':0,
    'remainingConcreteOverlaps':0,'protectedAssets':len(manifest['protected']),
    'sceneAndModelDocsAndPhysicsUnchanged':True,'candidateSHA256':sha(after)}
(OUT/'source-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
