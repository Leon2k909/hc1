"""Prove exact approved monitor placement, attributes, scope and physics retention."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import re
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
OUT=ROOT/'output/collider-monitor-accepted-20261029'
spec=importlib.util.spec_from_file_location('monitor_install',Path(__file__).with_name('install_accepted.py'))
I=importlib.util.module_from_spec(spec);spec.loader.exec_module(I)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((OUT/'installed.json').read_text());rel=Path('models/maps/collider/collider_structure.obj')
source=ROOT/'Assets'/rel
chair_out=ROOT/'output/collider-chair-accepted-20261029'
chair_path=chair_out/'installed.json'
chair=json.loads(chair_path.read_text()) if chair_path.exists() else None
chair_records={r['relative']:r for r in chair['files']} if chair else {}
for r in d['files']:
    expected=r['after']
    if r['relative'] in chair_records:
        next_record=chair_records[r['relative']]
        assert next_record['before']==expected
        assert sha(chair_out/'before'/r['relative'])==expected
        expected=next_record['after']
    assert sha(ROOT/'Assets'/r['relative'])==expected,r['relative']
for p,h in d['protectedOtherFiles'].items():assert sha(ROOT/p)==h,p
old=(OUT/'before'/rel).read_text().splitlines(keepends=True);removed=set(d['removedFaceLines'])
installed_snapshot=chair_out/'before'/rel if chair else source
assert installed_snapshot.read_text().startswith(''.join(line for i,line in enumerate(old,1) if i not in removed))
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
import collider_monitor as CM
m=K.Model();M.monitor(m,(1880.,-190.,381.),(-1,0),112,66,0);M.configure(m)
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
        elif line.startswith('o ') and not transform:active=line.strip()=='o collider_approved_monitor'
        elif line.startswith('f ') and active:
            ids=[[int(v)-1 for v in t.split('/')] for t in line.split()[1:]]
            out[(paint,tuple(sorted(tuple(round(float(x),6) for x in (*positions[v],*uv[t],*normals[n])) for v,t,n in ids)))]+=1
    return out
assert attrs(source)==attrs(I.TRIAL/'after.obj',True),'Approved UVs/normals/positions differ'
for p in d['retiredOldStandaloneResources']:assert not (ROOT/p).exists()
result={'approvedMonitorInstalled':True,'oldMonitorTrianglesRemaining':0,'approvedTriangles':sum(after.values()),
    'unrelatedFaceLinesAndOriginalAttributesPreserved':True,'approvedPositionsUVsAndNormalsExact':True,
    'sceneAndPhysicsUnchanged':True,'priorCaseAndCabinetSourceHashesPreserved':True,'sourceGeneratorMatchesExactly':True,
    'oldStandaloneResourcesRemoved':True,'editorUsed':False,'engineCompilation':'pending'}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
