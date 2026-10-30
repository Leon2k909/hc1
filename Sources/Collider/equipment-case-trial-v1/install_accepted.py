"""Replace exactly the approved case in source, without starting the editor."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/collider-case-accepted-20261029'
TRIAL=ROOT/'Assets/models/props/collider/equipment-case-trial-v1'
ORIGIN=np.array((-1150.,-350.,0.))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def key(paint,points):
    return paint,tuple(sorted(tuple(round(float(v),3) for v in p) for p in points))


def triangles(path,offset=np.zeros(3)):
    vertices=[];paint=''
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vertices.append(np.array((-a,n,z))+offset)
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f '):
            yield key(paint,[vertices[int(s.split('/')[0])-1] for s in line.split()[1:]])


def main():
    assert not (OUT/'installed.json').exists(),'The approved replacement is already installed'
    review=json.loads((ROOT/'Sources/Collider/equipment-case-trial-v1/candidate.json').read_text())
    check=json.loads((ROOT/'Sources/Collider/equipment-case-trial-v1/review.json').read_text())
    for rel,expected in review['originalAssetsSHA256'].items():assert sha(ROOT/rel)==expected,rel
    assert sha(TRIAL/'after.obj')==check['geometryVerification']['variants']['after']['meshSHA256']
    expected=Counter(triangles(TRIAL/'before.obj',ORIGIN));remaining=expected.copy()
    relative=Path('models/maps/collider/collider_detail.obj')
    source=ROOT/'Assets'/relative
    lines=source.read_text().splitlines(keepends=True)
    vertices=[];paint='';retained=[];removed=[]
    for number,line in enumerate(lines,1):
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vertices.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):
            signature=key(paint,[vertices[int(s.split('/')[0])-1] for s in line.split()[1:]])
            if remaining[signature]:
                remaining[signature]-=1;removed.append(number);continue
        retained.append(line)
    assert not +remaining and len(removed)==2420,(len(removed),sum((+remaining).values()))
    offsets=tuple(sum(line.startswith(prefix) for line in lines) for prefix in ('v ','vt ','vn '))
    extra=['\n# Accepted equipment case replacement at plan (-1150,-350,0)\n','o collider_approved_case\n']
    for line in (TRIAL/'after.obj').read_text().splitlines(keepends=True):
        if line.startswith(('#','mtllib ','o ')):continue
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);line=f'v {a-ORIGIN[0]:.3f} {z+ORIGIN[2]:.3f} {n+ORIGIN[1]:.3f}\n'
        elif line.startswith('f '):
            line='f '+' '.join('/'.join(str(int(v)+offsets[i]) for i,v in enumerate(s.split('/'))) for s in line.split()[1:])+'\n'
        extra.append(line)
    new_obj=''.join(retained+extra)
    before_count=sum(line.startswith('f ') for line in lines)
    assert sum(line.startswith('f ') for line in retained+extra)==before_count-2420+15568
    remaps=review['models']['after']['materials']
    mtl=source.with_suffix('.mtl');vmdl=source.with_suffix('.vmdl')
    old_doc=vmdl.read_text();old_mtl=mtl.read_text()
    additions=',\n'.join(f'\t\t\t\t\t\t\t{{ from = "{paint}.vmat" to = "{path}" }}' for paint,path in sorted(remaps.items()))
    pattern=r'(\bremaps\s*=\s*\[)([\s\S]*?)(\n\t{6}\])'
    new_doc,count=re.subn(pattern,lambda m:m[1]+m[2].rstrip().rstrip(',')+',\n'+additions+m[3],old_doc,count=1)
    assert count==1
    marker='\t\t\t{\n\t\t\t\t_class = "PhysicsShapeList"'
    assert new_doc[new_doc.index(marker):]==old_doc[old_doc.index(marker):]
    payloads={relative:new_obj,relative.with_suffix('.mtl'):old_mtl+''.join(f'newmtl {p}\nKd 1 1 1\nd 1\n' for p in sorted(remaps)),
        relative.with_suffix('.vmdl'):new_doc}
    OUT.mkdir(parents=True,exist_ok=True)
    records=[]
    for rel,text in payloads.items():
        target=ROOT/'Assets'/rel;backup=OUT/'before'/rel;backup.parent.mkdir(parents=True,exist_ok=True)
        backup.write_bytes(target.read_bytes())
        stage=OUT/'stage'/rel;stage.parent.mkdir(parents=True,exist_ok=True);stage.write_text(text,encoding='utf-8',newline='')
        records.append({'relative':rel.as_posix(),'before':sha(target),'after':sha(stage)})
    # Verify exact retained text and source isolation before writing any game asset.
    assert new_obj.startswith(''.join(line for i,line in enumerate(lines,1) if i not in set(removed)))
    completed=[]
    try:
        for record in records:
            rel=Path(record['relative']);target=ROOT/'Assets'/rel
            assert sha(target)==record['before']
            incoming=target.with_name(target.name+'.case-incoming')
            incoming.write_bytes((OUT/'stage'/rel).read_bytes());incoming.replace(target);completed.append(rel)
    except Exception:
        for rel in completed:(ROOT/'Assets'/rel).write_bytes((OUT/'before'/rel).read_bytes())
        raise
    # Delete the old standalone game resource, keeping only rollback data outside Assets.
    retired=[]
    for ext in ('.obj','.mtl','.vmdl'):
        old=TRIAL/('before'+ext)
        backup=OUT/'retired-before-resources'/old.name;backup.parent.mkdir(parents=True,exist_ok=True)
        backup.write_bytes(old.read_bytes());old.unlink();retired.append(old.relative_to(ROOT).as_posix())
    assert sha(ROOT/'Assets/scenes/maps/Collider/collider.scene')==review['originalAssetsSHA256']['Assets/scenes/maps/Collider/collider.scene']
    result={'status':'accepted-installed-in-map-sources','userApproved':True,'editorUsed':False,'engineCompilation':'pending',
        'placementPlan':ORIGIN.tolist(),'removedOldTriangles':2420,'addedApprovedTriangles':15568,
        'detailTrianglesBefore':before_count,'detailTrianglesAfter':before_count-2420+15568,
        'allOtherFaceLinesAndOriginalAttributeTablesPreserved':True,'sceneAndPhysicsUnchanged':True,
        'files':records,'retiredOldStandaloneResources':retired,'removedFaceLines':removed,
        'sourceGeneratorHook':'Tools/collider_equipment_case.py; collider_map.hardcase reviewed placement'}
    (OUT/'installed.json').write_text(json.dumps(result,indent=2)+'\n')
    (ROOT/'Sources/Collider/equipment-case-trial-v1/installed.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='removedFaceLines'}))


if __name__=='__main__':main()
