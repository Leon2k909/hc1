"""Verify the approved base, exact installation scope and original collision."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name]='1'
import psutil
process=psutil.Process()
process.nice(psutil.IDLE_PRIORITY_CLASS)
process.cpu_affinity(process.cpu_affinity()[-2:])
from pathlib import Path
from collections import Counter
import hashlib,importlib.util,json,re,sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
OUT=ROOT/'output/collider-column-base-accepted-20261030'
spec=importlib.util.spec_from_file_location('base_install',Path(__file__).with_name('install_accepted.py'))
I=importlib.util.module_from_spec(spec)
spec.loader.exec_module(I)
import collider_column_base as CB
import collider_map as M
import map_kit as K
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

d=json.loads((OUT/'installed.json').read_text())
rel=Path('models/maps/collider/collider_structure.obj')
source=ROOT/'Assets'/rel
for record in d['files']:
    assert sha(ROOT/'Assets'/record['relative'])==record['after'],record['relative']
assert sha(ROOT/d['generatorFile']['path'])==d['generatorFile']['after']
for path,h in d['protectedOtherFiles'].items():
    assert sha(ROOT/path)==h,path
review=json.loads(Path(__file__).with_name('review.json').read_text())
for path,h in review['proposalSourceSHA256'].items():
    if Path(path).stem!='before':
        assert sha(ROOT/path)==h,path

old=(OUT/'before'/rel).read_text().splitlines(keepends=True)
removed=set(d['removedFaceLines'])
assert len(removed)==12
assert source.read_text().startswith(''.join(line for i,line in enumerate(old,1) if i not in removed))
faces=Counter(I.I.triangles(source))
before=Counter(I.triangles(OUT/'retired-before-resources/before.obj'))
after=Counter(I.triangles(I.TRIAL/'after.obj'))
assert sum(before.values())==12 and sum(after.values())==35002
assert not before&faces and all(faces[key]==n for key,n in after.items())

old_doc=(OUT/'before'/rel.with_suffix('.vmdl')).read_bytes()
doc=source.with_suffix('.vmdl').read_bytes()
marker=b'PhysicsShapeList'
assert marker in old_doc and old_doc[old_doc.index(marker):]==doc[doc.index(marker):]
old_remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',old_doc.decode()))
remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc.decode()))
assert all(remaps[key]==path for key,path in old_remaps.items())
for path in remaps.values():
    assert (ROOT/'Assets'/path).is_file(),path

def attrs(path,transform=False):
    positions=[];uv=[];normals=[];paint='';out=Counter();active=transform
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);point=np.array((-a,n,z))
            positions.append(CB.ORIGIN+point if transform else point)
        elif line.startswith('vt '):
            uv.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);normals.append((-a,n,z))
        elif line.startswith('usemtl '):
            paint=line[7:]
        elif line.startswith('o ') and not transform:
            active=line.strip()=='o collider_approved_column_base'
        elif line.startswith('f ') and active:
            indices=[[int(v)-1 for v in s.split('/')] for s in line.split()[1:]]
            out[(paint,tuple(sorted(tuple(round(float(x),6) for x in (*positions[v],*uv[t],*normals[n]))
                                   for v,t,n in indices)))]+=1
    return out

assert attrs(source)==attrs(I.TRIAL/'after.obj',True)

def tris(model):
    return Counter(I.I.key(p,[points[0],points[i],points[i+1]])
                   for p,polys in model.polygons.items() for points,n in polys for i in range(1,len(points)-1))

def plain(value):
    if isinstance(value,np.ndarray):return value.tolist()
    return [plain(x) for x in value] if isinstance(value,(list,tuple)) else value

for e in (-960,960):
    for n in (-500,300):
        original=K.Model();M.box(original,e-44,e+44,n-44,n+44,0,8,'co_trim')
        current=K.Model();M.column_base(current,e,n);M.configure(current)
        assert plain(current.boxes)==plain(original.boxes) and plain(current.hulls)==plain(original.hulls)
        if (e,n)==(-960,-500):
            assert tris(current)==after
            for paint in current.polygons:
                assert current.material_overrides[paint]==remaps[paint+'.vmat']
        else:
            assert tris(current)==tris(original),'An unselected column base changed'

for path in d['retiredOldStandaloneResources']:
    assert not (ROOT/path).exists()
result={'approvedColumnBaseInstalled':True,'approvedTriangles':35002,'oldBaseTrianglesRemaining':0,
        'exactApprovedPositionsUVsNormalsAndMaterials':True,'unrelatedOriginalFacesAndAttributesPreserved':True,
        'fullColumnAndScenePreserved':True,'fullPhysicsUnchanged':True,'generatorPreservesAllFourOriginalClips':True,
        'otherThreeColumnBasesUnchanged':True,'priorAcceptedPropsPreserved':True,'sourceGeneratorMatchesExactly':True,
        'oldStandaloneResourcesRemoved':True,'editorUsed':False,'engineCompilation':'pending'}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
