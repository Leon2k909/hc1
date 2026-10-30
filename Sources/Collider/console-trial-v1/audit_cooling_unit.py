import os
for n in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[n]='1'
import psutil
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);p.cpu_affinity(p.cpu_affinity()[-2:])
from pathlib import Path
from collections import Counter
import sys,json
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import collider_map as M
def key(p,ps):return p,tuple(sorted(tuple(round(float(v),3) for v in pt) for pt in ps))
m=K.Model();e=-1470.
M.box(m,e-53,e+53,1710,1785,20,250,'co_steel',False)
for zz in range(43,230,17):M.box(m,e-44,e+44,1708,1710,zz,zz+7,'co_trim',False)
M._legacy_monitor(m,(e,1707,211),(0,-1),56,28,2)
expected=Counter(key(p,[ps[0],ps[i],ps[i+1]]) for p,polys in m.polygons.items() for ps,n in polys for i in range(1,len(ps)-1))
found=Counter();vs=[];paint='';near=Counter()
with (ROOT/'Assets/models/maps/collider/collider_machine.obj').open() as f:
    for line in f:
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vs.append((-a,n,z))
        elif line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):
            pts=[vs[int(t.split('/')[0])-1] for t in line.split()[1:]];k=key(paint,pts)
            if k in expected:found[k]+=1
            if all(-1524<=v[0]<=-1416 and 1702<=v[1]<=1786 and 19<=v[2]<=251 for v in pts):near[paint]+=1
print(json.dumps({'expected':sum(expected.values()),'matched':sum((expected&found).values()),'boundsMaterialTriangles':dict(near)}))
