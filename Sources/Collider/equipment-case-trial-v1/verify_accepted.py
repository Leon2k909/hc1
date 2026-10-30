"""Independent check of the approved map replacement and preserved collision."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import importlib.util
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/collider-case-accepted-20261029'
sys.path.insert(0,str(ROOT/'Tools'))
spec=importlib.util.spec_from_file_location('case_install',Path(__file__).with_name('install_accepted.py'))
I=importlib.util.module_from_spec(spec);spec.loader.exec_module(I)
d=json.loads((OUT/'installed.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cabinet_out=ROOT/'output/collider-cabinet-accepted-20261029'
cabinet_path=cabinet_out/'installed.json'
cabinet=json.loads(cabinet_path.read_text()) if cabinet_path.exists() else None
for record in d['files']:
    expected=record['after']
    if cabinet and record['relative']==cabinet['relative']:
        assert expected==cabinet['beforeSHA256']
        assert sha(cabinet_out/'before.obj')==expected
        expected=cabinet['afterSHA256']
    assert sha(ROOT/'Assets'/record['relative'])==expected,record['relative']
rel=Path('models/maps/collider/collider_detail.obj')
old_lines=(OUT/'before'/rel).read_text().splitlines(keepends=True)
# Prove the case's original scope against its installed snapshot; the later
# cabinet verifier separately proves that replacement and current case retention.
case_installed=cabinet_out/'before.obj' if cabinet else ROOT/'Assets'/rel
current=case_installed.read_text()
removed=set(d['removedFaceLines'])
assert current.startswith(''.join(line for i,line in enumerate(old_lines,1) if i not in removed))
before=Counter(I.triangles(OUT/'retired-before-resources/before.obj',I.ORIGIN))
all_faces=Counter(I.triangles(ROOT/'Assets'/rel))
assert not before & all_faces,'Old case render triangles remain'
approved=Counter(I.triangles(I.TRIAL/'after.obj',I.ORIGIN))
assert all(all_faces[k]==count for k,count in approved.items()),'Approved case differs from reviewed geometry'
old_doc=(OUT/'before'/rel.with_suffix('.vmdl')).read_bytes()
new_doc=(ROOT/'Assets'/rel.with_suffix('.vmdl')).read_bytes()
marker=b'PhysicsShapeList'
assert old_doc[old_doc.index(marker):]==new_doc[new_doc.index(marker):], 'Physics bytes changed'
import collider_map as M
import map_kit as K
regen=K.Model();M.hardcase(regen,-1150,-350,0,100,56,65,0);M.configure(regen)
actual=Counter(I.key(paint,[points[0],points[i],points[i+1]]) for paint,ps in regen.polygons.items()
    for points,n in ps for i in range(1,len(points)-1))
assert actual==approved,'Generator does not retain the accepted geometry'
assert len(regen.boxes)==1
assert np.allclose(regen.boxes[0][0],(-1150,-350,34)) and np.allclose(regen.boxes[0][2],(100,56,62))
for path in d['retiredOldStandaloneResources']:assert not (ROOT/path).exists(),path
synced=[];preserved=[]
for record in d['files']:
    rel=Path(record['relative']);primary=ROOT/'output/collider/stage/assets'/rel
    if primary.exists() and sha(primary)==record['before']:
        primary.write_bytes((ROOT/'Assets'/rel).read_bytes());synced.append(rel.as_posix())
    elif primary.exists() and sha(primary)==record['after']:synced.append(rel.as_posix())
    else:preserved.append(rel.as_posix())
result={'acceptedCaseInstalled':True,'oldCaseTrianglesRemaining':0,'approvedTriangles':sum(approved.values()),
    'unaffectedOriginalFaceLinesAndAttributesPreserved':True,'physicsSuffixByteIdentical':True,
    'regeneratedGeometryMatchesExactly':True,'oldStandaloneResourcesRemoved':True,
    'primaryStageSynchronized':synced,'newerStagedFilesPreserved':preserved,'editorUsed':False,'engineCompilation':'pending'}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
