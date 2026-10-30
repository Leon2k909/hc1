"""Identify an actual saved control-room monitor before changing its design."""
from pathlib import Path
from collections import Counter
import sys
import json
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import collider_map as M
m=K.Model();M.monitor(m,(1880,-190,381),(-1,0),112,66,0)
key=lambda paint,ps:(paint,tuple(sorted(tuple(round(float(v),3) for v in p) for p in ps)))
expected=Counter(key(p,[ps[0],ps[i],ps[i+1]]) for p,polys in m.polygons.items() for ps,n in polys for i in range(1,len(ps)-1))
v=[];paint='';remaining=expected.copy();local=[]
for line in (ROOT/'Assets/models/maps/collider/collider_structure.obj').read_text().splitlines():
    if line.startswith('v '):
        a,z,n=map(float,line.split()[1:]);v.append(np.array((-a,n,z)))
    elif line.startswith('usemtl '):paint=line[7:]
    elif line.startswith('f ') and paint in ('co_case','co_screens','co_beam'):
        ps=np.array([v[int(token.split('/')[0])-1] for token in line.split()[1:]])
        k=key(paint,ps)
        if remaining[k]:remaining[k]-=1
        if np.all(ps>=(1878,-249,345)) and np.all(ps<=(1885,-131,417)):local.append((paint,ps.tolist()))
result={'expectedTriangles':sum(expected.values()),'unmatchedTriangles':sum((+remaining).values()),'localTriangles':len(local),
    'localMaterials':dict(Counter(p for p,ps in local))}
out=ROOT/'output/asset-improvement-20261029/monitor';out.mkdir(parents=True,exist_ok=True)
(out/'baseline-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
