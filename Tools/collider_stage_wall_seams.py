"""Stage the bounded shell-face correction against the installed Collider mesh."""
from pathlib import Path
import hashlib
import json
import numpy as np
import map_kit as K
import collider_wall_seams as W

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/collider-wall-overlap-20261027'
RELATIVE = 'models/maps/collider/collider_machine.obj'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage():
    source = ROOT/'Assets'/RELATIVE
    destination = OUT/'stage/assets'/RELATIVE
    assert not destination.exists(), 'Use a new revision instead of overwriting a staged candidate'
    lines = source.read_text(encoding='utf-8').splitlines(keepends=True)
    vertices, uvs, normals = [], [], []
    retained, fragments, removed = [], [], []
    paint = None
    for number, line in enumerate(lines, 1):
        if line.startswith('v '):
            a,z,n = map(float,line.split()[1:])
            vertices.append(np.array((-a,n,z)))
        elif line.startswith('vt '):
            uvs.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vn '):
            a,z,n = map(float,line.split()[1:])
            normals.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):
            paint = line.split()[1]
        elif line.startswith('f ') and paint == 'co_concrete':
            indices = [[int(v) for v in word.split('/')] for word in line.split()[1:]]
            assert len(indices) == 3
            polygon = [np.concatenate((vertices[v-1],uvs[t-1],normals[n-1])) for v,t,n in indices]
            pieces, changed = W.trim(polygon)
            if changed:
                removed.append({'line':number, 'face':line.rstrip(),
                    'area':W.area(polygon), 'retainedArea':sum(map(W.area,pieces))})
                fragments.extend(pieces)
                continue
        retained.append(line)
    # Two side boxes: inner/outer faces, rear caps, tops and bottoms. The
    # four front-cap triangles at n674 do not share a plane and are retained.
    assert len(removed) == 20, ('Unexpected concrete shell partition',len(removed))
    extra = ['\n# Collider wall-seams-v1: remove shared concrete shell surfaces\n']
    vbase,tbase,nbase = len(vertices),len(uvs),len(normals)
    new_faces = []
    added = 0
    area_after = 0.
    for polygon in fragments:
        for i in range(1,len(polygon)-1):
            triangle = [polygon[0],polygon[i],polygon[i+1]]
            area = W.area(triangle)
            assert area > 1e-6
            direction = np.cross(triangle[1][:3]-triangle[0][:3],triangle[2][:3]-triangle[0][:3])
            assert np.dot(direction,triangle[0][5:]) > 0
            area_after += area
            tokens = []
            for point in triangle:
                assert np.isfinite(point).all()
                e,n,z,u,v,ne,nn,nz = point
                extra.extend([f'v {-e:.3f} {z:.3f} {n:.3f}\n',f'vt {u:.5f} {v:.5f}\n',
                    f'vn {-ne:.3f} {nz:.3f} {nn:.3f}\n'])
                tokens.append(f'{vbase+1}/{tbase+1}/{nbase+1}')
                vbase+=1; tbase+=1; nbase+=1
            new_faces.append('f '+' '.join(tokens)+'\n')
            added += 1
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(''.join(retained+extra+['usemtl co_concrete\n']+new_faces),encoding='utf-8',newline='')
    backup = OUT/'stage/before'/RELATIVE
    backup.parent.mkdir(parents=True,exist_ok=True)
    backup.write_bytes(source.read_bytes())
    protected = {}
    for directory in ('models/maps/collider','materials/collider'):
        for path in (ROOT/'Assets'/directory).rglob('*'):
            if path.is_file() and not path.name.endswith(('_c','.meta')) and path != source:
                protected[path.relative_to(ROOT/'Assets').as_posix()] = sha(path)
    protected['scenes/maps/Collider/collider.scene'] = sha(ROOT/'Assets/scenes/maps/Collider/collider.scene')
    manifest = {'revision':'collider-wall-seams-v1','relative':RELATIVE,'before':sha(source),'after':sha(destination),
        'removedFaces':removed,'addedTriangles':added,'beforeTriangles':sum(s.startswith('f ') for s in lines),
        'afterTriangles':sum(s.startswith('f ') for s in retained)+added,
        'removedArea':sum(r['area']-r['retainedArea'] for r in removed),'retainedFragmentArea':area_after,
        'protected':protected, 'sources':{p:sha(ROOT/p) for p in (
            'Tools/collider_wall_seams.py','Tools/collider_stage_wall_seams.py','Tools/collider_map.py')}}
    (OUT/'stage/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('protected','sources','removedFaces')}))


if __name__ == '__main__':
    stage()
