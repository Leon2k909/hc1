"""Chip the lower section of exposed convex stone corners in Veridant."""
from collections import defaultdict
from pathlib import Path
import random
import numpy as np

ROOT = Path(__file__).resolve().parents[1] / 'Assets/models/maps/veridant'
SOURCE = 'court-stair-rail-v1/base_without_court_rail_0.obj'
DEST = ROOT / 'low-corner-wear'
DEST.mkdir(exist_ok=True)
lines = (ROOT / SOURCE).read_text().splitlines()
arrays = {k: [tuple(map(float, line.split()[1:])) for line in lines if line.startswith(k+' ')]
          for k in ('v', 'vt', 'vn')}
vertices, uv, normals = (np.array(arrays[k]) for k in arrays)
groups = defaultdict(list)
material = ''
for index, line in enumerate(lines):
    if line.startswith('usemtl '):
        material = line.split()[1]
    if material != 'vr_stone' or not line.startswith('f '):
        continue
    refs = np.array([list(map(int, ref.split('/'))) for ref in line.split()[1:]])-1
    if len(refs) != 3:
        continue
    points = vertices[refs[:,0], :3]
    normal = normals[refs[0,2]]
    for axis, across in ((0,2),(2,0)):
        lo, hi = min(points[:,1]), max(points[:,1])
        if (np.ptp(points[:,axis]) < 1e-5 and abs(normal[axis]) > .999
            and len(set(points[:,across])) == 2 and hi-lo >= 27
            and any(abs(lo-level) <= 1 for level in (0,128,192,256))):
            key = (axis, points[0,axis], min(points[:,across]), max(points[:,across]), lo, hi, int(np.sign(normal[axis])))
            groups[key].append((index, points, uv[refs[:,1], :2]))

edges = defaultdict(list)
for key, members in groups.items():
    axis, fixed, start, end, lo, hi, sign = key
    if len(members) != 2 or end-start < 12:
        continue
    for across, inward in ((start,1),(end,-1)):
        y,x = (fixed,across) if axis == 0 else (across,fixed)
        edges[y,x,lo,hi].append((key,inward))

selected = []
used = set()
for edge, sides in sorted(edges.items()):
    if len(sides) != 2:
        continue
    sides = sorted(sides)
    (a,sa),(b,sb) = sides
    if a[0] != 0 or b[0] != 2 or sa != -b[-1] or sb != -a[-1] or a in used or b in used:
        continue
    selected.append((edge,sides))
    used.update((a,b))

extra, faces, removed = [], [], set()
counts = [len(a) for a in arrays.values()]
def emit(points, direction, axis, mapping):
    points = np.array(points)
    normal = np.cross(points[1]-points[0], points[2]-points[0])
    if np.linalg.norm(normal) < 1e-8:
        return
    if np.dot(normal,direction) < 0:
        normal = -normal
        points = points[::-1]
    normal /= np.linalg.norm(normal)
    tex = np.column_stack((points[:,2 if axis==0 else 0], points[:,1], np.ones(len(points)))) @ mapping
    refs = []
    for point, texture in zip(points,tex):
        for i,(prefix,value) in enumerate(zip(arrays,(point,texture,normal))):
            counts[i] += 1
            extra.append(prefix+' '+' '.join(f'{x:.6f}' for x in value))
        refs.append('/'.join(map(str,counts)))
    faces.append('f '+' '.join(refs))

for (y,x,lo,hi), ((a,sa),(b,sb)) in selected:
    mappings = []
    for key in (a,b):
        removed.update(member[0] for member in groups[key])
        _, p, t = groups[key][0]
        mappings.append(np.linalg.solve(np.column_stack((p[:,2 if key[0]==0 else 0],p[:,1],np.ones(3))),t))
    rng = random.Random(f'{x},{y},{lo}')
    centre = rng.uniform(7,13)
    peak = rng.uniform(.30,.60)
    profile = [(lo,0,0),(lo+3,.10,.10),(lo+centre-1,.13,.11),
               (lo+centre,peak,peak*.67),(lo+centre+2,.13,.12),(lo+24,0,0),(hi,0,0)]
    if hi-lo > 38 and rng.random() < .45:
        profile[-2:-2] = [(lo+18,.11,.12),(lo+19,.22,.37),(lo+21,.12,.10)]
    xa = a[3] if sa>0 else a[2]
    yb = b[3] if sb>0 else b[2]
    for (z,d,e),(z2,d2,e2) in zip(profile,profile[1:]):
        left,right = (y,z,x+sa*d),(y+sb*e,z,x)
        left2,right2 = (y,z2,x+sa*d2),(y+sb*e2,z2,x)
        emit([(y,z,xa),left,left2,(y,z2,xa)],(a[-1],0,0),0,mappings[0])
        emit([right,(yb,z,x),(yb,z2,x),right2],(0,0,b[-1]),2,mappings[1])
        emit([left,right,left2],(a[-1],0,b[-1]),0,mappings[0])
        emit([right,right2,left2],(a[-1],0,b[-1]),0,mappings[0])

if not selected:
    raise RuntimeError('No eligible stone corners matched')
mtl = next(l.split(maxsplit=1)[1] for l in lines if l.startswith('mtllib '))
(DEST/mtl).write_bytes((ROOT/SOURCE).with_name(mtl).read_bytes())
(DEST/'corners.obj').write_text('\n'.join([l for i,l in enumerate(lines) if i not in removed]+extra+['usemtl vr_stone']+faces)+'\n')
(DEST/'buildings.vmdl').write_text((ROOT/'veridant_buildings.vmdl').read_text().replace(SOURCE,'low-corner-wear/corners.obj'))
print(f'{len(selected)} convex corners', [edge[:3] for edge,_ in selected])
