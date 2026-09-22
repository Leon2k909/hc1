import json
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
models=json.loads((HERE/'conversion.json').read_text())['models']
materials=json.loads((HERE/'materials.json').read_text())['materials']
for m in models:
    if m['category']!='Optic':continue
    axis=np.array(next(b['head'][1:] for b in m['bones'] if b['name']=='tag_reticle_attach'))
    ps=[];fs=[];mat=group=None;vertices={}
    for line in (HERE/'optics_original'/f'{m["key"]}.obj').read_text().splitlines():
        f=line.split()
        if not f:continue
        if f[0]=='v':ps.append([float(x) for x in f[1:]])
        elif f[0]=='usemtl':mat=f[1]
        elif f[0] in ('g','o'):group=f[1]
        elif f[0]=='f' and not materials[m['materials'][mat]].get('optic_glass') and not any(t in m['materials'][mat] for t in ('stencil','depth_mask')):
            ids=[int(v.split('/')[0])-1 for v in f[1:]];idx=len(fs);fs.append((group,mat,ids))
            for i in ids:vertices.setdefault((group,mat,i),[]).append(idx)
    ps=np.array(ps);seen=set()
    for seed in range(len(fs)):
        if seed in seen:continue
        component=set();todo=[seed]
        while todo:
            i=todo.pop()
            if i in component:continue
            component.add(i);g,mt,ids=fs[i]
            for v in ids:todo.extend(n for n in vertices[(g,mt,v)] if n not in component)
        seen.update(component)
        hit=False
        for i in component:
            t=ps[fs[i][2]];a=np.vstack((t[:,:2].T,np.ones(3)))
            if abs(np.linalg.det(a))>1e-10 and min(np.linalg.solve(a,[*axis,1]))>=-1e-5:hit=True;break
        if not hit:continue
        coords=ps[list({v for i in component for v in fs[i][2]})]
        print(m['key'],fs[seed][0],m['materials'][fs[seed][1]].split('/')[-1],len(component),'bounds',coords.min(0).round(4).tolist(),coords.max(0).round(4).tolist())
