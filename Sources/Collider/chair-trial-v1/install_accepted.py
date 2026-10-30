"""Install only the user's approved chair; preserve the saved scene and physics."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import re
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import collider_chair as CM
OUT=ROOT/'output/collider-chair-accepted-20261029'
TRIAL=ROOT/'Assets/models/props/collider/chair-trial-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('case_install',ROOT/'Sources/Collider/equipment-case-trial-v1/install_accepted.py')
I=importlib.util.module_from_spec(spec);spec.loader.exec_module(I)


def triangles(path):
    vertices=[];paint=''
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vertices.append(CM.ORIGIN+CM.ROTATION@np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f '):yield I.key(paint,[vertices[int(t.split('/')[0])-1] for t in line.split()[1:]])


def main():
    assert not (OUT/'installed.json').exists(),'Chair already installed'
    candidate=json.loads((Path(__file__).parent/'candidate.json').read_text())
    for path,h in candidate['protectedSourceSHA256'].items():assert sha(ROOT/path)==h,path
    for name,record in candidate['models'].items():assert sha(TRIAL/(name+'.obj'))==record['meshSHA256']
    relative=Path('models/maps/collider/collider_structure.obj');source=ROOT/'Assets'/relative
    lines=source.read_text().splitlines(keepends=True);vertices=[];paint='';keep=[];removed=[]
    remaining=Counter(triangles(TRIAL/'before.obj'))
    for number,line in enumerate(lines,1):
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vertices.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):
            key=I.key(paint,[vertices[int(t.split('/')[0])-1] for t in line.split()[1:]])
            if remaining[key]:remaining[key]-=1;removed.append(number);continue
        keep.append(line)
    assert not +remaining and len(removed)==100
    offsets=tuple(sum(s.startswith(p) for s in lines) for p in ('v ','vt ','vn '))
    extra=['\n# Accepted operator chair, original placement and physics retained\n','o collider_approved_chair\n']
    for line in (TRIAL/'after.obj').read_text().splitlines(keepends=True):
        if line.startswith(('#','mtllib ','o ')):continue
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);e,nn,zz=CM.ORIGIN+CM.ROTATION@np.array((-a,n,z));line=f'v {-e:.3f} {zz:.3f} {nn:.3f}\n'
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);e,nn,zz=CM.ROTATION@np.array((-a,n,z));line=f'vn {-e:.6f} {zz:.6f} {nn:.6f}\n'
        elif line.startswith('f '):line='f '+' '.join('/'.join(str(int(v)+offsets[i]) for i,v in enumerate(t.split('/'))) for t in line.split()[1:])+'\n'
        extra.append(line)
    text=''.join(keep+extra)
    count=sum(l.startswith('f ') for l in lines);after_count=sum(l.startswith('f ') for l in keep+extra)
    assert after_count==count-100+candidate['models']['after']['triangles']
    remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',(TRIAL/'after.vmdl').read_text()))
    remaps={p:path for p,path in remaps.items() if p.startswith('op_')}
    assert len(remaps)==4
    mtl=source.with_suffix('.mtl');doc=source.with_suffix('.vmdl');old_doc=doc.read_text()
    assert not any(p in old_doc for p in remaps)
    additions=',\n'.join(f'\t\t\t\t\t\t\t{{ from = "{p}" to = "{path}" }}' for p,path in sorted(remaps.items()))
    pattern=r'(\bremaps\s*=\s*\[)([\s\S]*?)(\n\t{6}\])'
    new_doc,n=re.subn(pattern,lambda m:m[1]+m[2].rstrip().rstrip(',')+',\n'+additions+m[3],old_doc,count=1);assert n==1
    marker='PhysicsShapeList';assert new_doc[new_doc.index(marker):]==old_doc[old_doc.index(marker):]
    payloads={relative:text,relative.with_suffix('.mtl'):mtl.read_text()+''.join(f'newmtl {p[:-5]}\nKd 1 1 1\nd 1\n' for p in sorted(remaps)),relative.with_suffix('.vmdl'):new_doc}
    OUT.mkdir(parents=True,exist_ok=True);records=[]
    for rel,payload in payloads.items():
        target=ROOT/'Assets'/rel;backup=OUT/'before'/rel;stage=OUT/'stage'/rel
        backup.parent.mkdir(parents=True,exist_ok=True);stage.parent.mkdir(parents=True,exist_ok=True)
        backup.write_bytes(target.read_bytes());stage.write_text(payload,encoding='utf-8',newline='')
        records.append({'relative':rel.as_posix(),'before':sha(target),'after':sha(stage)})
    assert text.startswith(''.join(l for i,l in enumerate(lines,1) if i not in set(removed)))
    completed=[]
    try:
        for r in records:
            rel=Path(r['relative']);target=ROOT/'Assets'/rel;assert sha(target)==r['before']
            temporary=target.with_name(target.name+'.chair-incoming');temporary.write_bytes((OUT/'stage'/rel).read_bytes());temporary.replace(target);completed.append(rel)
    except Exception:
        for rel in completed:(ROOT/'Assets'/rel).write_bytes((OUT/'before'/rel).read_bytes())
        raise
    changed={'Assets/'+r['relative'] for r in records}
    protected={p:h for p,h in candidate['protectedSourceSHA256'].items() if p not in changed}
    for p,h in protected.items():assert sha(ROOT/p)==h,p
    retired=[]
    for ext in ('.obj','.mtl','.vmdl'):
        old=TRIAL/('before'+ext);backup=OUT/'retired-before-resources'/old.name
        backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(old.read_bytes());old.unlink();retired.append(old.relative_to(ROOT).as_posix())
    synced=[];preserved=[]
    for r in records:
        rel=Path(r['relative']);primary=ROOT/'output/collider/stage/assets'/rel
        if primary.exists() and sha(primary)==r['before']:primary.write_bytes((ROOT/'Assets'/rel).read_bytes());synced.append(rel.as_posix())
        else:preserved.append(rel.as_posix())
    result={'status':'accepted-installed-in-map-sources','userApproved':True,'editorUsed':False,'engineCompilation':'pending',
        'placementPlan':[1723.,-55.,256.],'removedOldTriangles':100,'addedApprovedTriangles':candidate['models']['after']['triangles'],
        'structureTrianglesBefore':count,'structureTrianglesAfter':after_count,'files':records,'removedFaceLines':removed,
        'protectedOtherFiles':protected,'sceneAndPhysicsUnchanged':True,'retiredOldStandaloneResources':retired,
        'primaryStageSynchronized':synced,'newerStagedFilesPreserved':preserved,'sourceGeneratorHook':'Tools/collider_chair.py; collider_map.control_desk selected chair'}
    for p in (OUT/'installed.json',Path(__file__).parent/'installed.json'):p.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='removedFaceLines'}))


if __name__=='__main__':main()
