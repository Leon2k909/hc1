"""Source-only replacement of the cabinet explicitly accepted by the user."""
from pathlib import Path
from collections import Counter
import importlib.util
import hashlib
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/collider-cabinet-accepted-20261029'
TRIAL=ROOT/'Assets/models/props/collider/west-cabinet-trial-v1'
ORIGIN=np.array((-430.,80.,0.))
spec=importlib.util.spec_from_file_location('case_install',ROOT/'Sources/Collider/equipment-case-trial-v1/install_accepted.py')
I=importlib.util.module_from_spec(spec);spec.loader.exec_module(I)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not (OUT/'installed.json').exists(),'Cabinet already installed'
    candidate=json.loads((Path(__file__).parent/'candidate.json').read_text())
    for path,expected in candidate['protectedSourceSHA256'].items():assert sha(ROOT/path)==expected,path
    assert sha(TRIAL/'after.obj')==candidate['models']['after']['sourceSHA256']
    remaining=Counter(I.triangles(TRIAL/'before.obj',ORIGIN))
    path=ROOT/'Assets/models/maps/collider/collider_detail.obj'
    lines=path.read_text().splitlines(keepends=True);vertices=[];paint='';keep=[];removed=[]
    for number,line in enumerate(lines,1):
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vertices.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):
            key=I.key(paint,[vertices[int(s.split('/')[0])-1] for s in line.split()[1:]])
            if remaining[key]:remaining[key]-=1;removed.append(number);continue
        keep.append(line)
    assert not +remaining and len(removed)==276
    offsets=tuple(sum(s.startswith(prefix) for s in lines) for prefix in ('v ','vt ','vn '))
    added=['\n# Accepted west cabinet, original physics/placement retained\n','o collider_approved_west_cabinet\n']
    for line in (TRIAL/'after.obj').read_text().splitlines(keepends=True):
        if line.startswith(('#','mtllib ','o ')):continue
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);line=f'v {a-ORIGIN[0]:.3f} {z:.3f} {n+ORIGIN[1]:.3f}\n'
        elif line.startswith('f '):
            line='f '+' '.join('/'.join(str(int(v)+offsets[i]) for i,v in enumerate(token.split('/'))) for token in line.split()[1:])+'\n'
        added.append(line)
    payload=''.join(keep+added)
    before_count=sum(s.startswith('f ') for s in lines);after_count=sum(s.startswith('f ') for s in keep+added)
    assert after_count==before_count-276+17044
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'before.obj').write_bytes(path.read_bytes())
    (OUT/'after.obj').write_text(payload,encoding='utf-8',newline='')
    before=sha(path);after=sha(OUT/'after.obj')
    temporary=path.with_name(path.name+'.cabinet-incoming');temporary.write_bytes((OUT/'after.obj').read_bytes());temporary.replace(path)
    assert sha(path)==after
    for p,h in candidate['protectedSourceSHA256'].items():
        if p!=path.relative_to(ROOT).as_posix():assert sha(ROOT/p)==h,p
    retired=[]
    for suffix in ('.obj','.mtl','.vmdl'):
        old=TRIAL/('before'+suffix);backup=OUT/'retired-before-resources'/old.name
        backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(old.read_bytes());old.unlink();retired.append(old.relative_to(ROOT).as_posix())
    primary=ROOT/'output/collider/stage/assets/models/maps/collider/collider_detail.obj'
    stage='preserved-newer-stage'
    if primary.exists() and sha(primary)==before:primary.write_bytes(path.read_bytes());stage='synchronized'
    result={'status':'accepted-installed-in-map-sources','userApproved':True,'editorUsed':False,'engineCompilation':'pending',
        'placementPlan':ORIGIN.tolist(),'relative':'models/maps/collider/collider_detail.obj','beforeSHA256':before,'afterSHA256':after,
        'removedOldTriangles':276,'addedApprovedTriangles':17044,'detailTrianglesBefore':before_count,'detailTrianglesAfter':after_count,
        'removedFaceLines':removed,'protectedOtherFiles':{p:h for p,h in candidate['protectedSourceSHA256'].items() if p!=path.relative_to(ROOT).as_posix()},
        'physicsAndSceneUnchanged':True,'retiredOldStandaloneResources':retired,'primaryStage':stage,
        'sourceGeneratorHook':'Tools/collider_west_cabinet.py; collider_map.detail west branch'}
    (OUT/'installed.json').write_text(json.dumps(result,indent=2)+'\n')
    (Path(__file__).parent/'installed.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='removedFaceLines'}))


if __name__=='__main__':main()
