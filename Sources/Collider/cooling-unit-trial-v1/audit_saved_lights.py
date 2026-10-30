"""Read-only spatial inventory: old saved geometry can predate the current generator."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import psutil
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);p.cpu_affinity(p.cpu_affinity()[-2:])
from pathlib import Path
from collections import Counter
import json
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
c=np.array((0.,825.,850.));axis=np.array((140.,445.,-350.));axis/=np.linalg.norm(axis)
result={}
for part in ('detail','structure','machine'):
    vs=[];paint='';counts={'wall':Counter(),'spot':Counter()};points={'wall':[],'spot':[]}
    with (ROOT/'Assets/models/maps/collider'/('collider_'+part+'.obj')).open() as f:
        for line in f:
            if line.startswith('v '):
                a,z,n=map(float,line.split()[1:]);vs.append(np.array((-a,n,z)))
            elif line.startswith('usemtl '):paint=line.split()[1]
            elif line.startswith('f '):
                ids=[int(s.split('/')[0])-1 for s in line.split()[1:]];a=vs[ids[0]]
                # Cheap broad rejection before array operations.
                if not ((abs(a[0]+960)<20 and abs(a[1]+540)<12 and 10<a[2]<40) or
                        (abs(a[0])<30 and abs(a[1]-825)<30 and abs(a[2]-850)<30)):continue
                pts=np.array([vs[v] for v in ids])
                if np.all(pts>=(-974,-546,16)) and np.all(pts<=(-946,-535,33)):
                    counts['wall'][paint]+=1;points['wall'].extend(pts.tolist())
                rel=pts-c;depth=rel@axis;radial=rel-depth[:,None]*axis
                if np.all(depth>=-8.01) and np.all(depth<=14.01) and np.max(np.linalg.norm(radial,axis=1))<=12.01:
                    counts['spot'][paint]+=1;points['spot'].extend(pts.tolist())
    result[part]={name:{'triangles':dict(counter),'bounds':[np.min(points[name],axis=0).tolist(),np.max(points[name],axis=0).tolist()] if points[name] else []}
                  for name,counter in counts.items()}
(Path(__file__).parent/'saved-lights-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
