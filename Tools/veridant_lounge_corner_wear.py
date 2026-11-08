"""Create a reversible render-only variant of one exposed limestone corner."""
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1] / 'Assets/models/maps/veridant'
SOURCE = 'court-stair-rail-v1/base_without_court_rail_0.obj'
FOLDER = ROOT / 'lounge-corner-wear'
FOLDER.mkdir(exist_ok=True)
lines = (ROOT / SOURCE).read_text().splitlines()
vertices = np.array([list(map(float, l.split()[1:4])) for l in lines if l.startswith('v ')])
uvs = np.array([list(map(float, l.split()[1:3])) for l in lines if l.startswith('vt ')])
normals = [l for l in lines if l.startswith('vn ')]
original_count = [len(vertices), len(uvs), len(normals)]
output, additions, surfaces = [], [], {}
paint = ''
removed = 0
for line in lines:
    if line.startswith('usemtl '):
        paint = line.split()[1]
    if paint == 'vr_stone' and line.startswith('f '):
        refs = np.array([list(map(int, ref.split('/'))) for ref in line.split()[1:]]) - 1
        points = vertices[refs[:,0]]
        for axis, fixed, across, outer in [(0,720,2,-530), (2,-560,0,670)]:
            corner = -560 if across == 2 else 720
            if (np.all(points[:,axis] == fixed) and set(points[:,across]) == {corner,outer}
                    and set(points[:,1]) == {0,272}):
                matrix = np.column_stack((points[:,across], points[:,1], np.ones(3)))
                surfaces[axis] = np.linalg.solve(matrix, uvs[refs[:,1]])
                removed += 1
                break
        else:
            output.append(line)
        continue
    output.append(line)
if removed != 4 or len(surfaces) != 2:
    raise RuntimeError(f'Expected four corner faces, matched {removed}')

faces = []
def emit(points, axis, expected):
    p = np.array(points)
    normal = np.cross(p[1]-p[0], p[2]-p[0])
    if np.dot(normal, expected) < 0:
        p = p[::-1]
        normal = -normal
    normal /= np.linalg.norm(normal)
    across = 2 if axis == 0 else 0
    tex = np.column_stack((p[:,across], p[:,1], np.ones(len(p)))) @ surfaces[axis]
    refs = []
    for point, uv in zip(p, tex):
        for i, (prefix, value) in enumerate(zip(('v','vt','vn'),(point,uv,normal))):
            additions.append(prefix+' '+' '.join(f'{v:.6f}' for v in value))
            original_count[i] += 1
        refs.append('/'.join(map(str,original_count)))
    faces.append('f '+' '.join(refs))

# A shallow bevel with uneven chip depths and heights, tapered at the ends.
profile = [(0,.01,.01),(6,.20,.19),(16,.42,.28),(19,.18,.17),(45,.17,.17),
           (78,.20,.16),(115,.16,.20),(135,.19,.17),(140,.62,.43),(142,.32,.30),
           (145,.19,.18),(155,.19,.18),(157,.45,.76),(159,.30,.48),(162,.16,.18),
           (173,.15,.18),(175,.52,.42),(178,.17,.18),(203,.17,.17),
           (229,.18,.18),(232,.35,.54),(236,.17,.17),(267,.16,.16),(272,.01,.01)]
for (z,a,b),(z2,a2,b2) in zip(profile,profile[1:]):
    left, right = (720,z,-560+a), (720-b,z,-560)
    left2, right2 = (720,z2,-560+a2), (720-b2,z2,-560)
    emit([(720,z,-530),left,left2,(720,z2,-530)],0,(1,0,0))
    emit([right,(670,z,-560),(670,z2,-560),right2],2,(0,0,-1))
    emit([left,right,left2],0,(1,0,-1))
    emit([right,right2,left2],0,(1,0,-1))

mtl = next(line.split(maxsplit=1)[1] for line in lines if line.startswith('mtllib '))
(FOLDER/mtl).write_bytes((ROOT/SOURCE).with_name(mtl).read_bytes())
(FOLDER/'corner.obj').write_text('\n'.join(output+additions+['usemtl vr_stone']+faces)+'\n')
model = (ROOT/'veridant_buildings.vmdl').read_text()
assert model.count(SOURCE) == 1
(FOLDER/'buildings.vmdl').write_text(model.replace(SOURCE,'lounge-corner-wear/corner.obj'))
