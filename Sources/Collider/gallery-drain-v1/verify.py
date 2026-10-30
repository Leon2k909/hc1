"""Check exported triangles and exact preservation independently of authoring."""
from pathlib import Path
import hashlib
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
STAGE=ROOT/'output/collider-gallery-drain-20261027/stage-v1'
BASE='models/maps/collider/collider_detail'
manifest=json.loads((STAGE/'manifest.json').read_text())
before=(STAGE/'before'/(BASE+'.obj')).read_text().splitlines()
after=(STAGE/'assets'/(BASE+'.obj')).read_text().splitlines()
marker=next(i for i,s in enumerate(after) if s.startswith('# gallery-drain-v1'))
attributes=lambda lines:[s for s in lines if s.startswith(('v ','vt ','vn '))]
assert attributes(before)==attributes(after[:marker])
# The retained source is an ordered subsequence; only 288 original triangle lines disappear.
j=0
removed=[]
for line in before:
    if j<marker and line==after[j]:j+=1
    else:removed.append(line)
assert all(s.startswith('f ') for s in removed) and len(removed)==288
assert all(not s.strip() for s in after[j:marker])
vertices=[]
normals=[]
bad=[]
areas=[]
for n,line in enumerate(after):
    if line.startswith('v '):vertices.append(np.array(list(map(float,line.split()[1:]))))
    elif line.startswith('vn '):normals.append(np.array(list(map(float,line.split()[1:]))))
    elif n>marker and line.startswith('f '):
        ids=[list(map(int,s.split('/'))) for s in line.split()[1:]]
        p=np.array([vertices[i[0]-1] for i in ids])
        cross=np.cross(p[1]-p[0],p[2]-p[0])
        area=np.linalg.norm(cross)/2
        normal=np.mean([normals[i[2]-1] for i in ids],axis=0)
        if not np.isfinite(p).all() or area<1e-9 or np.dot(cross,normal)<-1e-9:bad.append(n+1)
        areas.append(float(area))
assert not bad,('Degenerate or reversed added triangles',bad[:20])
physics='\t\t\t{\n\t\t\t\t_class = "PhysicsShapeList"'
left=(STAGE/'before'/(BASE+'.vmdl')).read_text()
right=(STAGE/'assets'/(BASE+'.vmdl')).read_text()
assert left[left.index(physics):]==right[right.index(physics):]
hash_file=lambda p:hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
assert all(hash_file(STAGE/'assets'/e['relative'])==e['after'] for e in manifest['files'])
installed=all(hash_file(ROOT/'Assets'/e['relative'])==e['after'] for e in manifest['files'])
result=dict(Success=True,AddedTriangles=len(areas),MinimumTriangleArea=min(areas),BadTriangles=bad,
            OriginalAttributesPreserved=True,OriginalRetainedFacesPreserved=True,RemovedOriginalTriangles=len(removed),
            PhysicsSourcePreserved=True,InstalledMatchesStage=installed)
(STAGE/'geometry-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
