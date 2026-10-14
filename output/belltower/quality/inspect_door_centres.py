from pathlib import Path
import json
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

root=Path(__file__).resolve().parents[3]
vertices=[]
used={}
paint=''
with (root/'Assets/models/maps/belltower/belltower_west.obj').open() as stream:
    for line in stream:
        if line.startswith('v '):
            a,b,c=map(float,line.split()[1:]); vertices.append((c,a,b))
        elif line.startswith('usemtl '):
            paint=line.split()[1]
        elif line.startswith('f ') and paint in [f'door_{k}' for k in 'abcde']:
            used.setdefault(paint,set()).update(int(v.split('/')[0])-1 for v in line.split()[1:])
records=[]
for paint,indices in used.items():
    points=np.array([vertices[i] for i in indices])
    planar,inverse=np.unique(points[:,:2],axis=0,return_inverse=True)
    pairs=cKDTree(planar).query_pairs(20,output_type='ndarray')
    graph=coo_matrix((np.ones(len(pairs)),(pairs[:,0],pairs[:,1])),shape=(len(planar),len(planar)))
    count,labels=connected_components(graph,directed=False)
    for label in range(count):
        group=points[labels[inverse]==label]
        lo,hi=group.min(axis=0),group.max(axis=0)
        records.append({'paint':paint,'centre':((lo+hi)/2).tolist(),'bounds':[lo.tolist(),hi.tolist()]})
output=root/'output/belltower/quality/doors-v1-centres.json'
output.write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records,indent=2))
