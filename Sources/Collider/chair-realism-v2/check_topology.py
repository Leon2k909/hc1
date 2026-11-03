from pathlib import Path
from collections import Counter
import json
p=Path(__file__).resolve().parent/'candidate/Assets/models/props/collider/chair-realism-v2/after.obj'
positions=[];paint='';edges=Counter();triangles=0
for line in p.read_text().splitlines():
    if line.startswith('v '):positions.append(tuple(map(float,line.split()[1:])))
    elif line.startswith('usemtl '):paint=line[7:]
    elif paint=='cloth' and line.startswith('f '):
        ps=[positions[int(t.split('/')[0])-1] for t in line.split()[1:]];triangles+=1
        for a,b in zip(ps,ps[1:]+ps[:1]):edges[tuple(sorted((a,b)))]+=1
result={'clothTriangles':triangles,'boundaryEdges':sum(v==1 for v in edges.values()),'nonManifoldEdges':sum(v>2 for v in edges.values()),'edgeMultiplicity':dict(Counter(edges.values()))}
assert result['boundaryEdges']==0 and result['nonManifoldEdges']==0
report=p.parents[5]/'verification.json'
data=json.loads(report.read_text());data['closedManifoldClothMeshes']=result
report.write_text(json.dumps(data,indent=2))
print(json.dumps(result))
