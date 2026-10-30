"""Replace both legacy valve instances with the user's exact approved surface revision."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import re
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import collider_valve as CV
import collider_services as S
import map_kit as K
OUT=ROOT/'output/collider-valve-accepted-20261029'
TRIAL=ROOT/'Assets/models/props/collider/valve-trial-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('case_install',ROOT/'Sources/Collider/equipment-case-trial-v1/install_accepted.py')
I=importlib.util.module_from_spec(spec);spec.loader.exec_module(I)

def triangles(path,at,facing):
    origin,rotation=CV.frame(at,facing);vertices=[];paint=''
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vertices.append(origin+rotation@np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f '):yield I.key(paint,[vertices[int(t.split('/')[0])-1] for t in line.split()[1:]])

def legacy_triangles(at,facing):
    # The legacy flanges always faced +north, even on the mirrored valve.
    # Match each actual old assembly instead of mirroring the left baseline.
    model=K.Model();S._legacy_valve(model,at,facing)
    for paint,polys in model.polygons.items():
        for ps,n in polys:
            for i in range(1,len(ps)-1):yield I.key(paint,[ps[0],ps[i],ps[i+1]])

def main():
    assert not (OUT/'installed.json').exists(),'Accepted valves are already installed'
    candidate=json.loads((Path(__file__).parent/'candidate.json').read_text())
    review=json.loads((Path(__file__).parent/'review.json').read_text())
    assert review['revision']=='surface-v2' and candidate['revision']=='surface-v2'
    for path,h in candidate['protectedSourceSHA256'].items():assert sha(ROOT/path)==h,path
    for path,h in review['materialSourceSHA256'].items():assert sha(ROOT/path)==h,path
    for name,d in candidate['models'].items():assert sha(TRIAL/(name+'.obj'))==d['meshSHA256']==review['modelSourceSHA256'][name]
    relative=Path('models/maps/collider/collider_detail.obj');source=ROOT/'Assets'/relative
    lines=source.read_text().splitlines(keepends=True);vertices=[];paint='';keep=[];removed=[]
    remaining=Counter()
    for at,facing in CV.PLACEMENTS:remaining.update(legacy_triangles(at,facing))
    old_count=sum(remaining.values());assert old_count==1356
    for number,line in enumerate(lines,1):
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vertices.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):
            key=I.key(paint,[vertices[int(t.split('/')[0])-1] for t in line.split()[1:]])
            if remaining[key]:remaining[key]-=1;removed.append(number);continue
        keep.append(line)
    assert not +remaining and len(removed)==old_count
    offsets=[sum(l.startswith(p) for l in lines) for p in ('v ','vt ','vn ')]
    local_lines=(TRIAL/'after.obj').read_text().splitlines(keepends=True)
    increments=[sum(l.startswith(p) for l in local_lines) for p in ('v ','vt ','vn ')]
    extra=[]
    for instance,(at,facing) in enumerate(CV.PLACEMENTS):
        origin,rotation=CV.frame(at,facing)
        extra+=['\n# Accepted weathered valve; original placement and physics retained\n',f'o collider_approved_valve_{instance}\n']
        for line in local_lines:
            if line.startswith(('#','mtllib ','o ')):continue
            if line.startswith('v '):
                a,z,n=map(float,line.split()[1:]);e,nn,zz=origin+rotation@np.array((-a,n,z));line=f'v {-e:.3f} {zz:.3f} {nn:.3f}\n'
            elif line.startswith('vn '):
                a,z,n=map(float,line.split()[1:]);e,nn,zz=rotation@np.array((-a,n,z));line=f'vn {-e:.6f} {zz:.6f} {nn:.6f}\n'
            elif line.startswith('f '):line='f '+' '.join('/'.join(str(int(v)+offsets[i]) for i,v in enumerate(t.split('/'))) for t in line.split()[1:])+'\n'
            extra.append(line)
        offsets=[a+b for a,b in zip(offsets,increments)]
    obj=''.join(keep+extra);before_count=sum(l.startswith('f ') for l in lines)
    after_count=sum(l.startswith('f ') for l in keep+extra)
    added=candidate['models']['after']['triangles']*2;assert added==40328 and after_count==before_count-old_count+added
    remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',(TRIAL/'after.vmdl').read_text()));assert len(remaps)==12
    mtl=source.with_suffix('.mtl');doc=source.with_suffix('.vmdl');old_doc=doc.read_text()
    assert not any(p in old_doc for p in remaps)
    additions=',\n'.join(f'\t\t\t\t\t\t\t{{ from = "{p}" to = "{path}" }}' for p,path in sorted(remaps.items()))
    new_doc,n=re.subn(r'(\bremaps\s*=\s*\[)([\s\S]*?)(\n\t{6}\])',lambda m:m[1]+m[2].rstrip().rstrip(',')+',\n'+additions+m[3],old_doc,count=1);assert n==1
    marker='PhysicsShapeList';assert new_doc[new_doc.index(marker):]==old_doc[old_doc.index(marker):]
    payloads={relative:obj,relative.with_suffix('.mtl'):mtl.read_text()+''.join(f'newmtl {p[:-5]}\nKd 1 1 1\nd 1\n' for p in sorted(remaps)),relative.with_suffix('.vmdl'):new_doc}
    OUT.mkdir(parents=True,exist_ok=True);records=[]
    for rel,text in payloads.items():
        target=ROOT/'Assets'/rel;backup=OUT/'before'/rel;stage=OUT/'stage'/rel
        backup.parent.mkdir(parents=True,exist_ok=True);stage.parent.mkdir(parents=True,exist_ok=True)
        backup.write_bytes(target.read_bytes());stage.write_text(text,encoding='utf-8',newline='')
        records.append({'relative':rel.as_posix(),'before':sha(target),'after':sha(stage)})
    assert obj.startswith(''.join(line for i,line in enumerate(lines,1) if i not in set(removed)))
    # Refuse a changed approved resource or source immediately before installation.
    for path,h in review['materialSourceSHA256'].items():assert sha(ROOT/path)==h,path
    completed=[]
    try:
        for record in records:
            rel=Path(record['relative']);target=ROOT/'Assets'/rel;assert sha(target)==record['before']
            temporary=target.with_name(target.name+'.valve-incoming');temporary.write_bytes((OUT/'stage'/rel).read_bytes());temporary.replace(target);completed.append(rel)
    except Exception:
        for rel in completed:(ROOT/'Assets'/rel).write_bytes((OUT/'before'/rel).read_bytes())
        raise
    changed={'Assets/'+r['relative'] for r in records};protected={p:h for p,h in candidate['protectedSourceSHA256'].items() if p not in changed}
    for p,h in protected.items():assert sha(ROOT/p)==h,p
    retired=[]
    for ext in ('.obj','.mtl','.vmdl'):
        old=TRIAL/('before'+ext);backup=OUT/'retired-before-resources'/old.name
        backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(old.read_bytes());old.unlink();retired.append(old.relative_to(ROOT).as_posix())
    synced=[];preserved=[]
    for record in records:
        rel=Path(record['relative']);primary=ROOT/'output/collider/stage/assets'/rel
        if primary.exists() and sha(primary)==record['before']:primary.write_bytes((ROOT/'Assets'/rel).read_bytes());synced.append(rel.as_posix())
        else:preserved.append(rel.as_posix())
    result={'status':'accepted-installed-in-map-sources','userApproved':True,'revision':'surface-v2','instances':2,
        'placements':[{'center':list(at),'facing':list(facing)} for at,facing in CV.PLACEMENTS],
        'removedOldTriangles':old_count,'addedApprovedTriangles':added,'detailTrianglesBefore':before_count,'detailTrianglesAfter':after_count,
        'files':records,'removedFaceLines':removed,'protectedOtherFiles':protected,'materialSourceSHA256':review['materialSourceSHA256'],
        'sceneAndPhysicsUnchanged':True,'retiredOldStandaloneResources':retired,'primaryStageSynchronized':synced,'newerStagedFilesPreserved':preserved,
        'sourceGeneratorHook':'Tools/collider_valve.py; collider_services.valve; collider_map.configure',
        'editorUsed':False,'engineCompilation':'pending'}
    for p in (OUT/'installed.json',Path(__file__).parent/'installed.json'):p.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('removedFaceLines','materialSourceSHA256','protectedOtherFiles')}))

if __name__=='__main__':main()
