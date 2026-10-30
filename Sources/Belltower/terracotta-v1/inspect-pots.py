from pathlib import Path
import json
import numpy as np

root=Path(__file__).resolve().parents[3]
rows=[]
for side in ('east','west'):
    path=root/f'Assets/models/maps/belltower/compiler-safe/{side}/{side}_011_clay_pot.obj'
    points=set()
    for line in path.open('rb'):
        if line.startswith(b'v '):
            y,z,x=map(float,line.split()[1:])
            if abs(z)<.001:points.add((x,y))
    while points:
        pending=[points.pop()];cluster=[]
        while pending:
            point=pending.pop();cluster.append(point)
            near={p for p in points if (p[0]-point[0])**2+(p[1]-point[1])**2<225}
            points-=near;pending.extend(near)
        assert len(cluster)==14,(side,len(cluster))
        centre=np.mean(cluster,axis=0).round(3).tolist()
        rows.append({'side':side,'centre_world':centre})
(root/'output/belltower/terracotta-v1/pots.json').write_text(json.dumps(rows,indent=2))
eye=np.array((-435.405945,-2046.49976))
print(json.dumps(sorted(rows,key=lambda r:np.linalg.norm(np.array(r['centre_world'])-eye))[:6],indent=2))
