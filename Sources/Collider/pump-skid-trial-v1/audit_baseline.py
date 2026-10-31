import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import psutil
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);p.cpu_affinity([14,15])
from pathlib import Path
from collections import Counter
import sys,json,numpy as np
sys.path.insert(0,'Tools')
import map_kit as K,collider_machinery as H,collider_detail_geometry as D,collider_map as M

def key(p,points):return p,tuple(sorted(tuple(round(float(v),3) for v in q) for q in points))
def keys(model):
    return Counter(key(p,[ps[0],ps[i],ps[i+1]]) for p,polys in model.polygons.items()
                   for ps,n in polys for i in range(1,len(ps)-1))
a=K.Model();b=K.Model()
H.instrument_cart(a,-850,-350,0,106,58,74,0)
D.hardcase(b,-850,-350,0,106,58,74,0,label=M.sign)
ka=keys(a);kb=keys(b);vs=[];paint='';found=Counter();near=Counter();points=[]
for line in Path('Assets/models/maps/collider/collider_detail.obj').read_text().splitlines():
    if line.startswith('v '):
        x,z,y=map(float,line.split()[1:]);vs.append(np.array((-x,y,z)))
    elif line.startswith('usemtl '):paint=line[7:]
    elif line.startswith('f '):
        pts=np.array([vs[int(t.split('/')[0])-1] for t in line.split()[1:]])
        if np.all(pts.min(axis=0)>=(-908,-389,-.1)) and np.all(pts.max(axis=0)<=(-790,-311,80)):
            found[key(paint,pts)]+=1;near[paint]+=1;points.extend(pts.tolist())
print(json.dumps({'expectedPumpTriangles':sum(ka.values()),'expectedCaseTriangles':sum(kb.values()),
                  'savedTrianglesInIsolatedEnvelope':sum(found.values()),'savedMaterials':dict(near),
                  'exactPumpMatches':sum((ka&found).values()),'exactCaseMatches':sum((kb&found).values()),
                  'savedBounds':[np.min(points,axis=0).tolist(),np.max(points,axis=0).tolist()] if points else []},indent=2))
