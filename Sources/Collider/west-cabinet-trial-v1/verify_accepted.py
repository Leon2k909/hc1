"""Verify the scoped cabinet replacement, generator parity and retained case."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/collider-cabinet-accepted-20261029'
sys.path.insert(0,str(ROOT/'Tools'))
spec=importlib.util.spec_from_file_location('cabinet_install',Path(__file__).with_name('install_accepted.py'))
I=importlib.util.module_from_spec(spec);spec.loader.exec_module(I)
d=json.loads((OUT/'installed.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
path=ROOT/'Assets'/d['relative'];assert sha(path)==d['afterSHA256']
for p,h in d['protectedOtherFiles'].items():assert sha(ROOT/p)==h,p
old=(OUT/'before.obj').read_text().splitlines(keepends=True);removed=set(d['removedFaceLines'])
assert path.read_text().startswith(''.join(line for i,line in enumerate(old,1) if i not in removed))
faces=Counter(I.I.triangles(path));before=Counter(I.I.triangles(OUT/'retired-before-resources/before.obj',I.ORIGIN))
after=Counter(I.I.triangles(I.TRIAL/'after.obj',I.ORIGIN))
assert not before&faces and all(faces[k]==count for k,count in after.items())
case_origin=np.array((-1150.,-350.,0.))
case=Counter(I.I.triangles(ROOT/'Assets/models/props/collider/equipment-case-trial-v1/after.obj',case_origin))
assert all(faces[k]==count for k,count in case.items()),'Previously approved case changed'
import collider_west_cabinet as W
import map_kit as K
m=K.Model();W.append(m)
regen=Counter(I.I.key(p,[ps[0],ps[i],ps[i+1]]) for p,polys in m.polygons.items() for ps,n in polys for i in range(1,len(ps)-1))
assert regen==after and len(m.boxes)==1
assert np.allclose(m.boxes[0][0],(-430,80,69)) and np.allclose(m.boxes[0][2],(48,60,138))
for p in d['retiredOldStandaloneResources']:assert not (ROOT/p).exists()
result={'approvedCabinetInstalled':True,'oldCabinetTrianglesRemaining':0,'approvedCabinetTriangles':sum(after.values()),
    'priorApprovedCasePreserved':True,'allOtherFaceLinesAndAttributeTablesPreserved':True,
    'modelDocAndPhysicsAndSavedSceneByteIdentical':True,'generatorGeometryMatchesExactly':True,
    'oldStandaloneResourcesRemoved':True,'editorUsed':False,'engineCompilation':'pending'}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
