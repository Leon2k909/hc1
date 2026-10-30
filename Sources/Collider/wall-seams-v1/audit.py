"""Read-only audit of same-facing coplanar concrete across Collider models."""
from collections import defaultdict
from pathlib import Path
import json
import argparse
import numpy as np

def cross(a, b):
    return float(a[0]*b[1]-a[1]*b[0])

def area(points):
    return abs(sum(cross(a,b) for a,b in zip(points, np.roll(points,-1,axis=0))))*.5 if len(points)>=3 else 0.

def intersection(left, right):
    result = list(left)
    direction = np.sign(sum(cross(a,b) for a,b in zip(right,np.roll(right,-1,axis=0))))
    for a,b in zip(right,np.roll(right,-1,axis=0)):
        previous = result
        result = []
        if not previous:
            break
        for p,q in zip(previous,previous[1:]+previous[:1]):
            dp,dq = cross(b-a,p-a)*direction,cross(b-a,q-a)*direction
            if dp>=-1e-8:
                result.append(p)
            if (dp>1e-8 and dq<-1e-8) or (dp<-1e-8 and dq>1e-8):
                result.append(p+(q-p)*(dp/(dp-dq)))
    return np.asarray(result)

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/collider-wall-overlap-20261027'
parser = argparse.ArgumentParser(description=__doc__)
variants = parser.add_mutually_exclusive_group()
variants.add_argument('--candidate', action='store_true')
variants.add_argument('--baseline', action='store_true')
args = parser.parse_args()
groups = defaultdict(list)
records = []
for name in ('structure', 'detail', 'machine', 'glass'):
    path = ROOT / f'Assets/models/maps/collider/collider_{name}.obj'
    if args.candidate and name == 'machine':
        path = OUT / 'stage/assets/models/maps/collider/collider_machine.obj'
    if args.baseline and name == 'machine':
        path = OUT / 'stage/before/models/maps/collider/collider_machine.obj'
    vertices = []
    material = ''
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if line.startswith('v '):
            a, z, n = map(float, line.split()[1:])
            vertices.append((-a, n, z))
        elif line.startswith('usemtl '):
            material = line[7:]
        elif line.startswith('f ') and material in ('co_wall', 'cf_wall', 'co_concrete', 'cf_concrete'):
            points = np.array([vertices[int(v.split('/')[0])-1] for v in line.split()[1:]])
            normal = np.cross(points[1]-points[0], points[2]-points[0])
            axis = int(np.argmax(abs(normal)))
            if np.ptp(points[:, axis]) > .002:
                continue
            sign = int(np.sign(normal[axis]))
            plane = round(float(points[0, axis]), 3)
            axes = [i for i in range(3) if i != axis]
            polygon = points[:, axes]
            if area(polygon) < .001:
                continue
            groups[(axis, plane, sign, name, material)].append(polygon)
            records.append({'model':name, 'material':material, 'line':number,
                'axis':axis, 'plane':plane, 'sign':sign, 'lo':points.min(0).tolist(), 'hi':points.max(0).tolist()})
hits = []
keys = list(groups)
for i, a in enumerate(keys):
    for b in keys[i+1:]:
        if a[:3] != b[:3] or a[3:] == b[3:]:
            continue
        pieces = [intersection(p,q) for p in groups[a] for q in groups[b]
            if np.all(p.max(0)>=q.min(0)) and np.all(q.max(0)>=p.min(0))]
        pieces = [p for p in pieces if area(p)>.01]
        overlap_area = sum(map(area,pieces))
        if overlap_area > .01:
            points = np.vstack(pieces)
            hits.append({'a':a, 'b':b, 'areaInches2':overlap_area,
                'bounds':[*points.min(0).tolist(),*points.max(0).tolist()]})
result = {'concreteTriangleCount':len(records), 'overlaps':hits, 'triangles':records}
OUT.mkdir(parents=True, exist_ok=True)
report = 'candidate-audit.json' if args.candidate else 'wall-overlap-audit.json' if args.baseline else 'installed-audit.json'
(OUT / report).write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({'concreteTriangleCount':len(records), 'overlaps':hits}))
