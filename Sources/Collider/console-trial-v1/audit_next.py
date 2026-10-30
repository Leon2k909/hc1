"""Read-only search for the next actual saved prop, never a draft approximation."""
import os
for n in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[n]='1'
import psutil
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);p.cpu_affinity(p.cpu_affinity()[-2:])
from pathlib import Path
from collections import Counter
import sys,json
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import collider_machinery as H
def key(p,points):return p,tuple(sorted(tuple(round(float(v),3) for v in a) for a in points))
models={}
for title,c,r in (('west-column-gauge',(-974.,-539.,120.),8),('west-far-column-gauge',(-974.,261.,120.),8),
                  ('pressure-vessel-gauge',(-1430.,1485.,178.),13),
                  ('cryostat-gauge',(-1606.,1099.,407.),12)):
    m=K.Model();H.gauge(m,c,(0,-1,0),r);models[title]=m
m=K.Model();H.instrument_cart(m,-850,-350,0,106,58,74,0);models['instrument-cart']=m
expected={name:Counter(key(p,[ps[0],ps[i],ps[i+1]]) for p,polys in m.polygons.items()
                      for ps,n in polys for i in range(1,len(ps)-1)) for name,m in models.items()}
wanted=set().union(*(set(c) for c in expected.values()));paints={p for p,ps in wanted}
found=Counter();geometry=Counter();actual_paints=Counter();vs=[];paint='';wanted_geometry={ps for p,ps in wanted}
with (ROOT/'Assets/models/maps/collider/collider_machine.obj').open() as f:
    for line in f:
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vs.append((-a,n,z))
        elif line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):
            k=key(paint,[vs[int(s.split('/')[0])-1] for s in line.split()[1:]])
            if k in wanted:found[k]+=1
            if k[1] in wanted_geometry:geometry[k[1]]+=1;actual_paints[paint]+=1
result={name:{'expectedTriangles':sum(c.values()),'matchedTriangles':sum((c&found).values()),'fullyPresent':not bool(+(c-found))}
        for name,c in expected.items()}
for name,c in expected.items():
    geom=Counter()
    for (paint,ps),count in c.items():geom[ps]+=count
    result[name]['geometryMatchedIgnoringMaterial']=sum((geom&geometry).values())
result['actualMatchedMaterials']=dict(actual_paints)
(Path(__file__).parent/'next-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
