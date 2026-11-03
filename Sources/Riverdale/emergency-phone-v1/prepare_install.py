"""Stage only the eight old wall phones' render-face removals and authored instance group."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
from pathlib import Path
from collections import Counter
import json,hashlib,sys,math
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/riverdale-emergency-phone-installed-20261031'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_emergency_phones as E,riverdale_hall as H
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
PLACEMENTS=[((1000,340,45),(-1,0)),((1000,1680,333),(-1,0)),((-1000,340,45),(1,0)),((-1000,1680,333),(1,0)),
            ((-905,2000,45),(0,-1)),((-880,2000,333),(0,-1)),((880,2000,333),(0,-1)),((-560,-200,45),(0,1))]
def signature(paint,points):return paint,tuple(sorted(tuple(round(float(v),3) for v in p) for p in points))
def local_triangles(path):
    points=[];paint=''
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);points.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f '):yield paint,[points[int(t.split('/')[0])-1] for t in line.split()[1:]]
def main():
    assert not (HERE/'installed.json').exists(),'Already installed'
    review=json.loads((HERE/'review.json').read_text());assert review['nativeEngineComparison']['NativeEngineRendering']
    for name,h in review['proposalSourceSHA256'].items():assert sha(ROOT/name)==h,name
    before=list(local_triangles(ROOT/'Assets/models/props/riverdale/emergency-phone-v1/before.obj'));assert len(before)==126
    remaining=Counter()
    for origin,out in PLACEMENTS:
        out=np.array((*out,0.));right=np.cross((0,0,1),out);back=-out;origin=np.array(origin,float)
        detail=K.Model();fine=K.Model()
        H.wall_phone(detail,fine,H.Face(origin[:2],out[:2]),0,float(origin[2]+7))
        # The old beacon's cap fan starts on a global axis, so rebuild its original fan per orientation.
        for model in (detail,fine):
            for paint,polys in model.polygons.items():
                for points,n in polys:
                    for i in range(1,len(points)-1):remaining[signature(paint,[points[0],points[i],points[i+1]])]+=1
        E.record(origin,out[:2])
    assert sum(remaining.values())==1008
    OUT.mkdir(parents=True,exist_ok=True);records=[]
    for stem,expected in [('riverdale_hall_detail',80),('riverdale_hall_fine',928)]:
        relative=f'Assets/models/maps/riverdale/{stem}.obj';path=ROOT/relative;raw=path.read_bytes();lines=raw.decode().splitlines(keepends=True)
        positions=[];paint='';keep=[];removed=[]
        for index,line in enumerate(lines):
            if line.startswith('v '):
                a,z,n=map(float,line.split()[1:]);positions.append((-a,n,z))
            elif line.startswith('usemtl '):paint=line.split()[1]
            elif line.startswith('f ') and paint in ('rv_door_yellow','rv_hall_plastic','rv_hall_signs','rv_hall_led_red'):
                key=signature(paint,[positions[int(t.split('/')[0])-1] for t in line.split()[1:]])
                if remaining[key]:remaining[key]-=1;removed.append(index);continue
            keep.append(line)
        assert len(removed)==expected,(stem,len(removed),expected)
        backup=OUT/'before'/relative;stage=OUT/'stage'/relative;backup.parent.mkdir(parents=True,exist_ok=True);stage.parent.mkdir(parents=True,exist_ok=True)
        backup.write_bytes(raw);stage.write_bytes(''.join(keep).encode())
        records.append(dict(path=relative,before=sha(path),after=sha(stage),removedFaceLines=removed,removedTriangles=expected))
    assert not +remaining
    ids=K.SceneIds('5f1c9a72-8e34-4b6d-a2c7-91e0d4b36f85');group=E.scene_group(ids)
    (OUT/'phone-group.json').write_text(json.dumps(group,indent=2)+'\n')
    scene=ROOT/'Assets/scenes/maps/Riverdale/riverdale.scene';backup=OUT/'before/Assets/scenes/maps/Riverdale/riverdale.scene';backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(scene.read_bytes())
    report=dict(userApproved=True,phoneCount=8,removedTriangles=1008,files=records,placements=PLACEMENTS,group=group,
        sceneSHA256=sha(scene),proposalSourceSHA256=review['proposalSourceSHA256'],publishedMapModelDocsUnchanged={str(p.relative_to(ROOT)).replace(chr(92),'/'):sha(p) for p in (ROOT/'Assets/models/maps/riverdale').glob('*.vmdl')},
        note='Phone bodies are shared scene instances; no render-geometry duplication in packed map models.')
    (OUT/'plan.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(phones=8,removedTriangles=1008,files=[r['path'] for r in records])))
if __name__=='__main__':main()
