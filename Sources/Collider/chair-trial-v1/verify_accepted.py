"""Prove exact approved chair placement, attributes, scope and physics retention."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import re
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
OUT=ROOT/'output/collider-chair-accepted-20261029'
spec=importlib.util.spec_from_file_location('chair_install',Path(__file__).with_name('install_accepted.py'))
I=importlib.util.module_from_spec(spec);spec.loader.exec_module(I)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((OUT/'installed.json').read_text());rel=Path('models/maps/collider/collider_structure.obj')
source=ROOT/'Assets'/rel
for r in d['files']:assert sha(ROOT/'Assets'/r['relative'])==r['after'],r['relative']
for p,h in d['protectedOtherFiles'].items():assert sha(ROOT/p)==h,p
old=(OUT/'before'/rel).read_text().splitlines(keepends=True);removed=set(d['removedFaceLines'])
assert source.read_text().startswith(''.join(line for i,line in enumerate(old,1) if i not in removed))
faces=Counter(I.I.triangles(source))
before=Counter(I.triangles(OUT/'retired-before-resources/before.obj'))
after=Counter(I.triangles(I.TRIAL/'after.obj'))
assert not before&faces and all(faces[k]==count for k,count in after.items())
old_doc=(OUT/'before'/rel.with_suffix('.vmdl')).read_bytes();doc=source.with_suffix('.vmdl').read_bytes()
marker=b'PhysicsShapeList';assert old_doc[old_doc.index(marker):]==doc[doc.index(marker):]
old_remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',old_doc.decode()))
remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc.decode()))
assert all(remaps[p]==path for p,path in old_remaps.items())
for p,path in remaps.items():assert (ROOT/'Assets'/path).is_file(),path
import collider_map as M
import map_kit as K
import collider_chair as CM
m=K.Model();CM.append(m);M.configure(m)
regen=Counter(I.I.key(p,[ps[0],ps[i],ps[i+1]]) for p,polys in m.polygons.items() for ps,n in polys for i in range(1,len(ps)-1))
assert regen==after and not m.boxes and not m.hulls
for paint in m.polygons:assert m.material_overrides[paint]==remaps[paint+'.vmat']

def attrs(path,transform=False):
    positions=[];uv=[];normals=[];paint='';out=Counter();active=transform
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);p=np.array((-a,n,z))
            positions.append(CM.ORIGIN+CM.ROTATION@p if transform else p)
        elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);n=np.array((-a,n,z));normals.append(CM.ROTATION@n if transform else n)
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('o collider_approved_chair'):active=True
        elif line.startswith('f ') and active:
            ids=[[int(v)-1 for v in t.split('/')] for t in line.split()[1:]]
            out[(paint,tuple(sorted(tuple(round(float(x),6) for x in (*positions[v],*uv[t],*normals[n])) for v,t,n in ids)))]+=1
    return out
assert attrs(source)==attrs(I.TRIAL/'after.obj',True),'Approved UVs/normals/positions differ'

def model_triangles(model):
    return Counter(I.I.key(p,[ps[0],ps[i],ps[i+1]]) for p,polys in model.polygons.items()
        for ps,n in polys for i in range(1,len(ps)-1))
def plain(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,(list,tuple)):return [plain(v) for v in value]
    return value
station=K.Model();legacy=K.Model()
M.control_desk(station,1,-55.,256.);M._legacy_control_desk(legacy,1,-55.,256.)
assert model_triangles(station)==model_triangles(legacy)-before+after,'Station generator changed unrelated geometry'
assert plain(station.boxes)==plain(legacy.boxes) and plain(station.hulls)==plain(legacy.hulls),'Station collision changed'
for side,n,z in ((-1,-55.,256.),(1,95.,256.),(1,-220.,560.)):
    a=K.Model();b=K.Model();M.control_desk(a,side,n,z);M._legacy_control_desk(b,side,n,z)
    assert model_triangles(a)==model_triangles(b) and plain(a.boxes)==plain(b.boxes),'Other station changed'
for p in d['retiredOldStandaloneResources']:assert not (ROOT/p).exists()
result={'approvedChairInstalled':True,'oldChairTrianglesRemaining':0,'approvedTriangles':sum(after.values()),
    'unrelatedFaceLinesAndOriginalAttributesPreserved':True,'approvedPositionsUVsAndNormalsExact':True,
    'sceneAndPhysicsUnchanged':True,'priorCaseAndCabinetSourceHashesPreserved':True,'stationCollisionUnchanged':True,'otherStationsUnchanged':True,'sourceGeneratorMatchesExactly':True,
    'oldStandaloneResourcesRemoved':True,'editorUsed':False,'engineCompilation':'pending'}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
