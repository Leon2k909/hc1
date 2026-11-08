from pathlib import Path
import json
R=Path('C:/sbox-projects/hc1/forked-shooter-main');vs=[];mat='';adj={}
for l in (R/'Assets/models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.obj').read_text().splitlines():
    if l.startswith('v '):vs.append(tuple(float(x) for x in l.split()[1:]))
    elif l.startswith('usemtl '):mat=l.split()[1]
    elif l.startswith('f ') and mat=='cb_red':
        pts=[vs[int(x.split('/')[0])-1] for x in l.split()[1:]];h={p[1] for p in pts}
        if h not in ({40.,54.},{44.,58.}):continue
        for p in pts:adj.setdefault(p,set()).update(pts)
seen=set();out=[]
for p in adj:
    if p in seen:continue
    todo=[p];component=[]
    while todo:
        q=todo.pop()
        if q in seen:continue
        seen.add(q);component.append(q);todo.extend(adj[q]-seen)
    lo=[min(q[i] for q in component) for i in range(3)];hi=[max(q[i] for q in component) for i in range(3)]
    if abs(hi[0]-lo[0]-12)<.02 and abs(hi[2]-lo[2]-12)<.02:out.append({'e':-(lo[0]+hi[0])/2,'n':(lo[2]+hi[2])/2,'base':lo[1]})
print(json.dumps({'remaining_plain_red_vases':len(out),'placements':out},indent=2))
