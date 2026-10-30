"""Find an actual old luminaire in saved source without touching the editor."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import psutil
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);p.cpu_affinity(p.cpu_affinity()[-2:])
from pathlib import Path
from collections import Counter
import json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import collider_detail_geometry as D
import collider_machinery as H
def key(p,points):return p,tuple(sorted(tuple(round(float(v),3) for v in pt) for pt in points))
m=K.Model();e=-960;n=-500
D.plate(m,(e-12,n-43,17),(e+12,n-38,31),'co_trim',2)
D.plate(m,(e-9,n-44,23),(e+9,n-42,28),'co_white',.7)
models={'wall-washer':('detail',m)}
m=K.Model();origin=np.array((0,825,850.));target=np.array((140,1270,500.));direction=K.normalise(target-origin)
H.tube(m,origin-direction*8,origin+direction*12,12,'co_trim',20)
H.tube(m,origin+direction*12,origin+direction*14,9,'co_white',20)
models['machine-spotlight']=('machine',m)
result={}
for name,(part,m) in models.items():
    expected=Counter(key(p,[ps[0],ps[i],ps[i+1]]) for p,polys in m.polygons.items() for ps,n in polys for i in range(1,len(ps)-1))
    remaining=expected.copy();vs=[];paint=''
    with (ROOT/'Assets/models/maps/collider'/('collider_'+part+'.obj')).open() as f:
        for line in f:
            if line.startswith('v '):
                a,z,n=map(float,line.split()[1:]);vs.append((-a,n,z))
            elif line.startswith('usemtl '):paint=line.split()[1]
            elif line.startswith('f ') and paint in m.polygons:
                k=key(paint,[vs[int(s.split('/')[0])-1] for s in line.split()[1:]])
                if remaining[k]:remaining[k]-=1
    result[name]={'sourcePart':part,'triangles':sum(expected.values()),'matched':sum(expected.values())-sum(remaining.values()),'fullyPresent':not bool(+remaining)}
(Path(__file__).parent/'next-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
