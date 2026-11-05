"""Geometry, imported-resource and saved-map checks for the review candidate."""
from pathlib import Path
import json,hashlib
import numpy as np
ROOT=Path(__file__).absolute().parents[3]
OUT=ROOT/'output/riverside/roof-ac-v1'
manifest=json.loads((OUT/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,digest in manifest['protected'].items():assert sha(ROOT/p)==digest,'Protected source changed: '+p
for p,digest in manifest['files'].items():assert sha(ROOT/p)==digest,'Imported review asset differs: '+p
reports=[]
for lod in range(3):
    p=ROOT/'Assets/models/props/riverside/roof_ac_v1'/f'roof_ac_lod{lod}.obj'
    vs=[];ns=[];bad=deg=triangles=0
    for line in p.read_text().splitlines():
        t=line.split()
        if not t:continue
        if t[0]=='v':vs.append(np.array(list(map(float,t[1:4]))))
        elif t[0]=='vn':ns.append(np.array(list(map(float,t[1:4]))))
        elif t[0]=='f':
            indices=[list(map(int,a.split('/'))) for a in t[1:]]
            a,b,c=[vs[i[0]-1] for i in indices];n=np.cross(b-a,c-a)
            nn=sum((ns[i[2]-1] for i in indices),np.zeros(3));area=np.linalg.norm(n)
            deg+=int(area<1e-7);bad+=int(area>1e-7 and np.dot(n,nn)<-1e-7);triangles+=1
    assert not bad and not deg,(lod,bad,deg)
    assert triangles==manifest['triangles'][lod]
    world=np.array(vs)[:,[2,0,1]]
    reports.append(dict(lod=lod,triangles=triangles,inverted=bad,degenerate=deg,
                        world_min=world.min(axis=0).tolist(),world_max=world.max(axis=0).tolist()))
model=(ROOT/'Assets'/manifest['resource']).read_text()
assert 'PhysicsShape' not in model and 'PhysicsHull' not in model
assert manifest['triangles'][0]<4000 and manifest['triangles'][0]>manifest['triangles'][1]>manifest['triangles'][2]
compiled=json.loads((OUT/'native-compile.json').read_text())
assert all(i['result']['Success'] for i in compiled)
result=dict(PreviewOnly=True,SavedMapAndSourcePreserved=True,NoNewCollision=True,Models=reports,
            CompiledResources=len(compiled),LegacyTriangles=manifest['removed_old_triangles'])
(OUT/'validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
