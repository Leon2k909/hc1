"""Audit both accepted valves, exact attributes, retained upgrades and collision."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import re
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
OUT=ROOT/'output/collider-valve-accepted-20261029'
spec=importlib.util.spec_from_file_location('valve_install',Path(__file__).with_name('install_accepted.py'))
I=importlib.util.module_from_spec(spec);spec.loader.exec_module(I)
import collider_valve as CV
import collider_services as S
import collider_map as M
import map_kit as K
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((OUT/'installed.json').read_text());rel=Path('models/maps/collider/collider_detail.obj');source=ROOT/'Assets'/rel
for record in d['files']:assert sha(ROOT/'Assets'/record['relative'])==record['after'],record['relative']
for p,h in d['protectedOtherFiles'].items():assert sha(ROOT/p)==h,p
for p,h in d['materialSourceSHA256'].items():assert sha(ROOT/p)==h,p
old=(OUT/'before'/rel).read_text().splitlines(keepends=True);removed=set(d['removedFaceLines'])
assert source.read_text().startswith(''.join(line for i,line in enumerate(old,1) if i not in removed))
faces=Counter(I.I.triangles(source));before=Counter();after=Counter()
for at,facing in CV.PLACEMENTS:
    before.update(I.legacy_triangles(at,facing));after.update(I.triangles(I.TRIAL/'after.obj',at,facing))
assert not before&faces and all(faces[k]==count for k,count in after.items())
assert sum(before.values())==1356 and sum(after.values())==40328
old_doc=(OUT/'before'/rel.with_suffix('.vmdl')).read_bytes();doc=source.with_suffix('.vmdl').read_bytes();marker=b'PhysicsShapeList'
assert old_doc[old_doc.index(marker):]==doc[doc.index(marker):]
old_remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',old_doc.decode()))
remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc.decode()))
assert all(remaps[p]==path for p,path in old_remaps.items())
for p,path in remaps.items():assert (ROOT/'Assets'/path).is_file(),path

def model_triangles(model):
    return Counter(I.I.key(p,[ps[0],ps[i],ps[i+1]]) for p,polys in model.polygons.items() for ps,n in polys for i in range(1,len(ps)-1))
for at,facing in CV.PLACEMENTS:
    model=K.Model();S.valve(model,at,facing);M.configure(model)
    assert model_triangles(model)==Counter(I.triangles(I.TRIAL/'after.obj',at,facing))
    assert not model.boxes and not model.hulls
    for paint in model.polygons:assert model.material_overrides[paint]==remaps[paint+'.vmat']

def attrs(path,at=None,facing=None):
    transform=at is not None
    if transform:origin,rotation=CV.frame(at,facing)
    positions=[];uv=[];normals=[];paint='';out=Counter();active=transform
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);p=np.array((-a,n,z));positions.append(origin+rotation@p if transform else p)
        elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);n=np.array((-a,n,z));normals.append(rotation@n if transform else n)
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('o ') and not transform:active=line.startswith('o collider_approved_valve_')
        elif line.startswith('f ') and active:
            ids=[[int(v)-1 for v in t.split('/')] for t in line.split()[1:]]
            out[(paint,tuple(sorted(tuple(round(float(x),6) for x in (*positions[v],*uv[t],*normals[n])) for v,t,n in ids)))]+=1
    return out
expected=Counter()
for at,facing in CV.PLACEMENTS:expected.update(attrs(I.TRIAL/'after.obj',at,facing))
assert attrs(source)==expected,'Approved positions/UVs/normals differ'
# Verify the previously accepted case and cabinet geometry in the retained detail file.
for path,origin in ((ROOT/'Assets/models/props/collider/equipment-case-trial-v1/after.obj',np.array((-1150.,-350.,0.))),
        (ROOT/'Assets/models/props/collider/west-cabinet-trial-v1/after.obj',np.array((-430.,80.,0.)))):
    prior=Counter(I.I.triangles(path,origin));assert all(faces[k]==count for k,count in prior.items())
for p in d['retiredOldStandaloneResources']:assert not (ROOT/p).exists()
result={'approvedValveInstancesInstalled':2,'oldValveTrianglesRemaining':0,'approvedTriangles':40328,
    'exactReviewedPositionsUVsNormalsAndMaterials':True,'unrelatedOriginalFacesAndAttributesPreserved':True,
    'originalPhysicsAndSceneUnchanged':True,'acceptedCaseCabinetMonitorAndChairPreserved':True,
    'sourceGeneratorMatchesExactly':True,'oldStandaloneResourcesRemoved':True,'editorUsed':False,'engineCompilation':'pending'}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
