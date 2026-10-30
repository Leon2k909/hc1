"""Check both exported cabinet resources and preserve the accepted game sources."""
from pathlib import Path
import hashlib
import json
import re
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/asset-improvement-20261029/west-cabinet'
ASSET=ROOT/'Assets/models/props/collider/west-cabinet-trial-v1'
d=json.loads((OUT/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
accepted_path=ROOT/'output/collider-cabinet-accepted-20261029/installed.json'
accepted=json.loads(accepted_path.read_text()) if accepted_path.exists() else None
guards=dict(d['protectedSourceSHA256'])
if accepted:
    path='Assets/'+accepted['relative']
    assert guards[path]==accepted['beforeSHA256']
    guards[path]=accepted['afterSHA256']
for path,expected in guards.items():assert sha(ROOT/path)==expected,path
reports={};physics=[]
for name in ('before','after'):
    directory=ROOT/'output/collider-cabinet-accepted-20261029/retired-before-resources' if accepted and name=='before' else ASSET
    vertices=[];uv=[];normals=[];areas=[];bad=0
    for line in (directory/(name+'.obj')).read_text().splitlines():
        if line.startswith('v '):vertices.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vt '):uv.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vn '):normals.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('f '):
            ids=[[int(v)-1 for v in token.split('/')] for token in line.split()[1:]]
            p=np.array([vertices[v] for v,t,n in ids]);cross=np.cross(p[1]-p[0],p[2]-p[0]);area=np.linalg.norm(cross)*.5
            assert area>1e-8,(name,'degenerate');areas.append(area)
            for v,t,n in ids:assert np.isfinite(np.concatenate((vertices[v],uv[t],normals[n]))).all()
            if np.dot(cross,np.mean([normals[n] for v,t,n in ids],axis=0))<-1e-7:bad+=1
    assert bad==0,(name,bad)
    doc=(directory/(name+'.vmdl')).read_bytes();marker=b'PhysicsShapeList';physics.append(doc[doc.index(marker):])
    remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc.decode()))
    for path in remaps.values():assert (ROOT/'Assets'/path).is_file(),path
    reports[name]={'triangles':len(areas),'windingErrors':bad,'degenerateTriangles':0,
        'minimumTriangleArea':min(areas),'finiteUVsAndNormals':True,'materialCount':len(remaps)}
assert physics[0]==physics[1]
result={'acceptedCaseAndGameSourcesPreserved':True,'identicalCabinetCollisionBytes':True,
    'variants':reports,'candidateInstalledInMap':bool(accepted),'engineCompiled':False,'editorUsed':False}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
