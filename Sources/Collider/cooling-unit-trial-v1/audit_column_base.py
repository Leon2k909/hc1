import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import psutil
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);p.cpu_affinity(p.cpu_affinity()[-2:])
from pathlib import Path
from collections import Counter
import json
ROOT=Path(__file__).resolve().parents[3];vs=[];paint='';foot=Counter();context=Counter()
with (ROOT/'Assets/models/maps/collider/collider_structure.obj').open() as f:
    for line in f:
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vs.append((-a,n,z))
        elif line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):
            pts=[vs[int(s.split('/')[0])-1] for s in line.split()[1:]]
            if not all(-1004.01<=a<=-915.99 and -544.01<=b<=-455.99 for a,b,z in pts):continue
            if all(-.001<=z<=8.001 for a,b,z in pts):foot[paint]+=1
            elif all(7.999<=z<=440.001 for a,b,z in pts):context[paint]+=1
print(json.dumps({'baseTriangles':dict(foot),'columnContextTriangles':dict(context)}))
