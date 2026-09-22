"""Find opaque geometry crossing each imported optic's aiming axis."""
import json
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
models=json.loads((HERE/'conversion.json').read_text())['models']
materials=json.loads((HERE/'materials.json').read_text())['materials']
report=[]
for model in models:
    if model['category']!='Optic':continue
    key=model['key']; target=next(b['head'] for b in model['bones'] if b['name']=='tag_reticle_attach')
    positions=[]; triangles=[]; material=group=None
    for line in (HERE/'optics_original'/f'{key}.obj').read_text().splitlines():
        fields=line.split()
        if not fields:continue
        if fields[0]=='v':positions.append([float(v) for v in fields[1:]])
        elif fields[0]=='usemtl':material=fields[1]
        elif fields[0] in ('g','o'):group=fields[1]
        elif fields[0]=='f' and not materials[model['materials'][material]].get('optic_glass'):
            triangles.append((group,material,[int(v.split('/')[0])-1 for v in fields[1:]]))
    hits={}
    for group,material,ids in triangles:
        vertices=np.array([positions[i] for i in ids])
        matrix=np.vstack((vertices[:,:2].T,np.ones(3)))
        if abs(np.linalg.det(matrix))<1e-10:continue
        weights=np.linalg.solve(matrix,[target[1],target[2],1])
        if min(weights)<-1e-5:continue
        x=round(float(weights@vertices[:,2]),5)
        hit=hits.setdefault((group,material,x),dict(group=group,material=model['materials'][material],x=x,triangles=0,vertices=[]))
        hit['triangles']+=1;hit['vertices'].extend(vertices.tolist())
    for hit in hits.values():
        vertices=np.array(hit.pop('vertices'));hit['min']=vertices.min(axis=0).tolist();hit['max']=vertices.max(axis=0).tolist()
    item=dict(key=key,axis=target[1:],caps=list(hits.values()));report.append(item)
    if hits: print(json.dumps(item))
(HERE/'qa/optic-caps.json').write_text(json.dumps(report,indent=2))
