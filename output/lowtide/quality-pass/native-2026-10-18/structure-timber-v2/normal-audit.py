"""Check normals on the installed upper column shafts, without changing geometry."""
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[5]
reports=[]
for bank, cy in [('east',-740),('west',740)]:
    vertices=[]; normals=[]; selected=[]; paint=''
    path=ROOT/f'Assets/models/maps/lowtide/lowtide_{bank}.obj'
    with path.open() as file:
        for line in file:
            if line.startswith('v '):
                v=tuple(map(float,line.split()[1:4])); vertices.append((v[2],v[0],v[1]))
            elif line.startswith('vn '):
                n=tuple(map(float,line.split()[1:4])); normals.append((n[2],n[0],n[1]))
            elif line.startswith('usemtl '): paint=line.split()[1]
            elif paint=='iron_black' and line.startswith('f '):
                for corner in line.split()[1:]:
                    v,_,n=corner.split('/')
                    p=vertices[int(v)-1]
                    if 190<p[2]<290 and np.hypot(p[0]-630,p[1]-cy)<6:
                        selected.append((int(v)-1,int(n)-1))
    selected=list(set(selected))
    assert selected, f'No column samples for {bank}'
    p=np.array([vertices[v] for v,n in selected]); n=np.array([normals[n] for v,n in selected])
    radial=p[:,:2]-[630,cy]; radial/=np.linalg.norm(radial,axis=1)[:,None]
    dots=np.sum(radial*n[:,:2],axis=1)
    assert np.isfinite(n).all() and np.min(dots)>.99
    reports.append({'bank':bank,'uniqueShaftCorners':len(selected),'normalLengths':[float(x) for x in [np.linalg.norm(n,axis=1).min(),np.linalg.norm(n,axis=1).max()]],'minimumRadialDot':float(dots.min())})
out=Path(__file__).with_name('normal-audit.json')
out.write_text(json.dumps(reports,indent=2)+'\n')
print(json.dumps(reports,indent=2))
