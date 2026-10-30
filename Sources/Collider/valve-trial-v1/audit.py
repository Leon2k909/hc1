"""Find the actual installed overhead shutoff valve before creating a proposal."""
from pathlib import Path
from collections import Counter
import json
import hashlib
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import collider_services as S

def key(p,ps):return p,tuple(sorted(tuple(round(float(v),3) for v in pt) for pt in ps))

def main():
    m=K.Model();S.valve(m,(-1280.,280.,770.),(1,0,0))
    expected=Counter(key(p,[ps[0],ps[i],ps[i+1]]) for p,polys in m.polygons.items() for ps,n in polys for i in range(1,len(ps)-1))
    findings=[]
    for name in ('detail','structure','machine'):
        path=ROOT/f'Assets/models/maps/collider/collider_{name}.obj';vs=[];paint='';found=Counter()
        for line in path.read_text().splitlines():
            if line.startswith('v '):
                a,z,n=map(float,line.split()[1:]);vs.append((-a,n,z))
            elif line.startswith('usemtl '):paint=line[7:]
            elif line.startswith('f ') and paint in m.polygons:
                k=key(paint,[vs[int(t.split('/')[0])-1] for t in line.split()[1:]])
                if expected[k]:found[k]+=1
        matched=sum((expected&found).values())
        findings.append({'source':path.relative_to(ROOT).as_posix(),'expectedTriangles':sum(expected.values()),'matchedTriangles':matched,
            'allMatchedExactly':found==expected,'sourceSHA256':hashlib.sha256(path.read_bytes()).hexdigest()})
    out=ROOT/'output/asset-improvement-20261029/valve';out.mkdir(parents=True,exist_ok=True)
    (out/'baseline-audit.json').write_text(json.dumps(findings,indent=2)+'\n');print(json.dumps(findings))
    assert any(d['allMatchedExactly'] for d in findings),'Valve is not installed; choose another baseline'

if __name__=='__main__':main()
