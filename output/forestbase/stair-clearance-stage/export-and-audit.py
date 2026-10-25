import sys,os,json,hashlib,re
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
root=Path.cwd();sys.path.insert(0,str(root/'Tools'))
import forestbase_map as M, forestbase_cargo as C, forestbase_validate as V
out=root/'output/forestbase/stair-clearance-stage';before=root/'output/forestbase/stair-clearance-before'
C.ISLANDS=tuple((owner,name,(600,480) if name=='command service' else center,rows,cols,tiers,angle) for owner,name,center,rows,cols,tiers,angle in C.ISLANDS)
old=M.build(visual_chunks=['logistics'])['logistics']
p=out/'expected-before';M.K.write_model(p,'models/maps/forestbase','logistics',old)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for x in p.iterdir():
 if x.suffix in ('.obj','.mtl','.vmdl'):assert sha(x)==sha(before/'Assets/models/maps/forestbase'/x.name),('Baseline source parity',x)
V.audit(radius=24,output=out/'routes-before')
C.ISLANDS=tuple((owner,name,(600,250) if name=='command service' else center,rows,cols,tiers,angle) for owner,name,center,rows,cols,tiers,angle in C.ISLANDS)
new=M.build(visual_chunks=['logistics'])['logistics']
p=out/'models/maps/forestbase';M.K.write_model(p,'models/maps/forestbase','logistics',new)
after=V.audit(radius=24,output=out/'routes-after')
assert not after['problems'],after['problems']
assert len(old.boxes)==len(new.boxes)==96 and len(old.hulls)==len(new.hulls)==4
changes=[]
import numpy as np
for i,(a,b) in enumerate(zip(old.boxes,new.boxes)):
 if np.array_equal(a[0],b[0]):
  assert all(np.array_equal(a[k],b[k]) for k in range(3)) and a[3]==b[3];continue
 assert np.allclose(np.asarray(b[0])-a[0],(0,-230,0))
 assert np.array_equal(a[1],b[1]) and np.array_equal(a[2],b[2]) and a[3]==b[3]
 changes.append(i)
assert len(changes)==5
for a,b in zip(old.hulls,new.hulls):assert np.array_equal(a[0],b[0]) and a[1]==b[1]
assert sha(p/'logistics.mtl')==sha(before/'Assets/models/maps/forestbase/logistics.mtl')
for x in p.glob('logistics_hulls_*.obj'):assert sha(x)==sha(before/'Assets/models/maps/forestbase'/x.name)
report={'scope':'Source parity, five translated cargo boxes, unchanged hulls/materials/counts, and all-stair source-grid regression; requires fresh native navigation/controller retest.','oldCenter':[600,480],'newCenter':[600,250],'boxes':96,'movedBoxIndices':changes,'hulls':4,'routeChecks':len(after['checks']),'files':{x.name:sha(x) for x in p.iterdir() if x.suffix in ('.obj','.mtl','.vmdl')}}
(out/'geometry-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
