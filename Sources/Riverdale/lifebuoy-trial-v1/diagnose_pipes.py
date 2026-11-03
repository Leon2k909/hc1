from pathlib import Path
from collections import defaultdict,Counter
import json,math
ROOT=Path.cwd();all_faces=defaultdict(Counter);runs=[]
for path in (ROOT/'Assets/models/maps/riverdale').glob('riverdale_hall*.obj'):
    if 'hulls' in path.name:continue
    vertices=[];paint='';faces=[];parent={}
    def find(x):
        parent.setdefault(x,x)
        if parent[x]!=x:parent[x]=find(parent[x])
        return parent[x]
    for line in path.open():
        p=line.split()
        if not p:continue
        if p[0]=='v':a,z,n=map(float,p[1:4]);vertices.append((-a,n,z))
        elif p[0]=='usemtl':paint=p[1]
        elif p[0]=='f' and paint=='rv_pipe':
            pts=[vertices[int(t.split('/')[0])-1] for t in p[1:]]
            sig=tuple(sorted(pts));all_faces[sig][path.stem]+=1
            lo=[min(v[i] for v in pts) for i in range(3)];hi=[max(v[i] for v in pts) for i in range(3)]
            if hi[2]-lo[2]>100 and hi[0]-lo[0]<45 and hi[1]-lo[1]<45:
                faces.append(pts)
                for p in pts[1:]:parent[find(p)]=find(pts[0])
    groups=defaultdict(list)
    for pts in faces:groups[find(pts[0])]+=pts
    for pts in groups.values():
        pts=set(pts);e=sum(p[0] for p in pts)/len(pts);n=sum(p[1] for p in pts)/len(pts)
        r=sum(math.hypot(p[0]-e,p[1]-n) for p in pts)/len(pts)
        runs.append(dict(model=path.stem,e=round(e,3),n=round(n,3),r=round(r,3),z=[min(p[2] for p in pts),max(p[2] for p in pts)]))
duplicates=[dict(models=dict(c),example=sig) for sig,c in all_faces.items() if sum(c.values())>1]
overlaps=[]
for i,a in enumerate(runs):
    for b in runs[i+1:]:
        d=math.hypot(a['e']-b['e'],a['n']-b['n'])
        if d<a['r']+b['r']+.4 and min(a['z'][1],b['z'][1])>max(a['z'][0],b['z'][0]):overlaps.append([a,b,round(d-a['r']-b['r'],3)])
report=dict(verticalRuns=runs,overlappingRuns=overlaps,duplicateFaces=len(duplicates),duplicateExamples=duplicates[:4])
out=ROOT/'output/asset-improvement-20261031/riverdale-lifebuoy/pipe-diagnosis.json';out.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
