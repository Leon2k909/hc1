from pathlib import Path
from array import array
from collections import Counter
import json
import numpy as np

root = Path(__file__).resolve().parent
result = {}
for side in ('east', 'west'):
    path = Path(f'Assets/models/maps/belltower/belltower_{side}.obj')
    vertices = [[0., 0., 0.]]
    faces = array('I')
    materials = []
    material = None
    for line in path.open('rb'):
        if line.startswith(b'v '):
            vertices.append(list(map(float, line.split()[1:])))
        elif line.startswith(b'usemtl '):
            material = line.split()[1].decode()
        elif line.startswith(b'f '):
            faces.extend(int(t.split(b'/')[0]) for t in line.split()[1:])
            materials.append(material)
    v = np.array(vertices)
    f = np.frombuffer(faces, dtype=np.uint32).reshape(-1, 3)
    cross = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    area = np.linalg.norm(cross, axis=1)
    indices = np.flatnonzero(area == 0)
    result[side] = {'faces': len(f), 'exact_zero_area_faces': len(indices),
        'zero_area_materials': Counter(materials[i] for i in indices),
        'examples': [{'face': int(i), 'material': materials[i], 'vertices': v[f[i]].tolist()} for i in indices[:10]]}
    print(json.dumps(result[side]), flush=True)
(root / 'degenerate-faces.json').write_text(json.dumps(result, indent=2) + '\n')
