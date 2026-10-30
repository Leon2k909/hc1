"""Prove exact console integration, original collision and unrelated source retention."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
import psutil
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);p.cpu_affinity(p.cpu_affinity()[-2:])
from pathlib import Path
from collections import Counter
import hashlib,importlib.util,json,re,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
OUT=ROOT/'output/collider-console-accepted-20261030'
spec=importlib.util.spec_from_file_location('console_install',Path(__file__).with_name('install_accepted.py'))
I=importlib.util.module_from_spec(spec);spec.loader.exec_module(I)
import collider_console as CM
import collider_chair as CH
import collider_map as M
import map_kit as K
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((OUT/'installed.json').read_text());rel=Path('models/maps/collider/collider_structure.obj');source=ROOT/'Assets'/rel
for r in d['files']:assert sha(ROOT/'Assets'/r['relative'])==r['after'],r['relative']
for path,h in d['protectedOtherFiles'].items():assert sha(ROOT/path)==h,path
review=json.loads(Path(__file__).with_name('review.json').read_text())
for path,h in review['proposalSourceSHA256'].items():
    if Path(path).stem!='before':assert sha(ROOT/path)==h,path
old=(OUT/'before'/rel).read_text().splitlines(keepends=True);removed=set(d['removedFaceLines'])
assert source.read_text().startswith(''.join(line for i,line in enumerate(old,1) if i not in removed))
faces=Counter(I.I.triangles(source));before=Counter(I.triangles(OUT/'retired-before-resources/before.obj'))
after=Counter(I.triangles(I.TRIAL/'after.obj'))
assert sum(before.values())==688 and sum(after.values())==27334
assert not before&faces and all(faces[k]==n for k,n in after.items())
old_doc=(OUT/'before'/rel.with_suffix('.vmdl')).read_bytes();doc=source.with_suffix('.vmdl').read_bytes();marker=b'PhysicsShapeList'
assert old_doc[old_doc.index(marker):]==doc[doc.index(marker):]
old_remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',old_doc.decode()))
remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc.decode()))
assert all(remaps[key]==path for key,path in old_remaps.items())
for key,path in remaps.items():assert (ROOT/'Assets'/path).is_file(),path

def attrs(path,transform=False):
    positions=[];uv=[];normals=[];paint='';out=Counter();active=transform
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);pt=np.array((-a,n,z));positions.append(CM.ORIGIN+CM.ROTATION@pt if transform else pt)
        elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);n=np.array((-a,n,z));normals.append(CM.ROTATION@n if transform else n)
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('o ') and not transform:active=line.strip()=='o collider_approved_console'
        elif line.startswith('f ') and active:
            ids=[[int(v)-1 for v in s.split('/')] for s in line.split()[1:]]
            out[(paint,tuple(sorted(tuple(round(float(x),6) for x in (*positions[v],*uv[t],*normals[n])) for v,t,n in ids)))]+=1
    return out
assert attrs(source)==attrs(I.TRIAL/'after.obj',True)

def tris(model):
    return Counter(I.I.key(p,[ps[0],ps[i],ps[i+1]]) for p,polys in model.polygons.items()
                   for ps,n in polys for i in range(1,len(ps)-1))
def plain(v):
    if isinstance(v,np.ndarray):return v.tolist()
    return [plain(x) for x in v] if isinstance(v,(list,tuple)) else v
new=K.Model();CM.append(new);M.configure(new)
assert tris(new)==after and not new.boxes and not new.hulls
for paint in new.polygons:assert new.material_overrides[paint]==remaps[paint+'.vmat']
station=K.Model();legacy=K.Model();chair=K.Model();CH.append(chair)
M.control_desk(station,1,-55.,256.);M._legacy_control_desk(legacy,1,-55.,256.)
assert tris(station)==after+tris(chair)
assert plain(station.boxes)==plain(legacy.boxes) and plain(station.hulls)==plain(legacy.hulls)
for side,n,z in ((-1,-55.,256.),(1,95.,256.),(1,-220.,560.)):
    a=K.Model();b=K.Model();M.control_desk(a,side,n,z);M._legacy_control_desk(b,side,n,z)
    assert tris(a)==tris(b) and plain(a.boxes)==plain(b.boxes)
for path in d['retiredOldStandaloneResources']:assert not (ROOT/path).exists()
result={'approvedConsoleInstalled':True,'oldConsoleTrianglesRemaining':0,'approvedTriangles':sum(after.values()),
    'exactApprovedPositionsUVsNormalsAndMaterials':True,'unrelatedOriginalFacesAndAttributesPreserved':True,
    'sceneAndFullPhysicsUnchanged':True,'priorAcceptedChairMonitorValvesCaseAndCabinetPreserved':True,
    'stationCollisionUnchanged':True,'otherStationsUnchanged':True,'sourceGeneratorMatchesExactly':True,
    'oldStandaloneResourcesRemoved':True,'editorUsed':False,'engineCompilation':'pending'}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
