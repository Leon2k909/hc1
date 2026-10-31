"""Check the actual OBJ for round openings, closed grid junctions and continuous bend UVs."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import psutil
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);p.cpu_affinity(p.cpu_affinity()[-2:])
from pathlib import Path
from collections import defaultdict
import json,math,numpy as np

ROOT=Path(__file__).resolve().parents[3];vs=[];uv=[];paint='';triangles=[];bend=defaultdict(list)
for line in (ROOT/'Assets/models/props/collider/pump-skid-trial-v1/after.obj').read_text().splitlines():
    if line.startswith('v '):
        a,z,n=map(float,line.split()[1:]);vs.append(np.array((-a,n,z)))
    elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
    elif line.startswith('usemtl '):paint=line[7:]
    elif line.startswith('f ') and paint in ('ps_guard','ps_outlet_skin'):
        ids=[[int(v)-1 for v in t.split('/')] for t in line.split()[1:]];pts=np.array([vs[v] for v,t,n in ids])
        if paint=='ps_outlet_skin':
            for v,t,n in ids:bend[tuple(vs[v])].append(uv[t])
        elif np.all((pts[:,0]>=-.002)&(pts[:,0]<=12.002)):
            radius=np.linalg.norm(pts[:,1:]-np.array((7.,40.)),axis=1)
            if np.all(abs(radius-8.1)<.003):
                angle=np.arctan2(pts[:,2]-40,pts[:,1]-7)
                angle=np.where(angle<math.radians(-12)-.01,angle+math.tau,angle)
                triangles.append(np.stack((pts[:,0],angle*8.1),axis=-1))
assert triangles and bend
tris=np.array(triangles);a=tris[:,0];b=tris[:,1]-a;c=tris[:,2]-a
cross=lambda x,y:x[...,0]*y[...,1]-x[...,1]*y[...,0]
den=cross(b,c);valid=abs(den)>1e-9
def covered(point):
    q=np.array(point)-a
    s=np.divide(cross(q,c),den,out=np.full_like(den,-999),where=valid)
    t=np.divide(cross(b,q),den,out=np.full_like(den,-999),where=valid)
    return bool(np.any(valid&(s>=-.002)&(t>=-.002)&(s+t<=1.002)))
ta,tb=np.radians((-12,192))
for x in (1.5,4.5,7.5,10.5):
    for row in range(6):
        angle=ta+(tb-ta)*(row+.5)/6
        assert not covered((x,angle*8.1)),('Blocked intended opening',x,row)
for x in (3.,6.,9.):
    for row in range(1,6):
        angle=ta+(tb-ta)*row/6
        assert covered((x,angle*8.1)),('Unintended diamond gap',x,row)
for point,coords in bend.items():
    first=np.array(coords[0])
    for current in coords[1:]:
        delta=abs(np.array(current)-first);delta[1]=abs(delta[1]-round(delta[1]))
        assert delta.max()<.000021,('Bend UV seam',point,coords)
result={'intendedRoundGuardOpenings':24,'unintendedGuardGridGaps':0,'testedClosedGridJunctions':15,
        'outletVerticesChecked':len(bend),'outletUVSeams':0,'validatedFromActualExportedOBJ':True}
(ROOT/'output/asset-improvement-20261030/pump-skid/surface-repair-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
