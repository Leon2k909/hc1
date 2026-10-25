"""Read actual authored timber faces and locate large panels/door intersections."""
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/door-obstruction'


def main():
    result={}
    for name in ('veridant_buildings','veridant_dress'):
        vertices=[None];paint=None;faces=[]
        path=ROOT/f'Assets/models/maps/veridant/{name}.obj'
        for number,line in enumerate(path.open()):
            if line.startswith('v '):
                a,b,c=map(float,line.split()[1:]);vertices.append(np.array((-a,c,b)))
            elif line.startswith('usemtl '):paint=line.split()[1]
            elif line.startswith('f ') and ('timber' in paint or 'wood' in paint):
                pts=np.array([vertices[int(t.split('/')[0])] for t in line.split()[1:]])
                lo,hi=pts.min(axis=0),pts.max(axis=0)
                if hi[2]-lo[2]>=70 and max(hi[:2]-lo[:2])>=2:
                    faces.append({'line':number+1,'paint':paint,'lo':lo.tolist(),'hi':hi.tolist()})
        result[name]=faces
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'wood-face-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    for name,rows in result.items():
        print(name,'vertical wood triangles',len(rows))
        grouped={}
        for row in rows:
            key=tuple(row['lo']+row['hi']);grouped[key]=grouped.get(key,0)+1
        print(json.dumps([{'bounds':k,'triangles':n} for k,n in grouped.items()]))


if __name__=='__main__':main()
