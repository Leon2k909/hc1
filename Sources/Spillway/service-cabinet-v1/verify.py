from pathlib import Path
from collections import Counter
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/spillway/service-cabinet-v1'
sys.path.insert(0,str(ROOT/'Tools'))
import riverdale_splice as S
plan=json.loads((OUT/'install-plan.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for rel,expected in plan['files'].items():assert sha(ROOT/rel)==expected,'Installed mismatch: '+rel
for rel,expected in plan['guards'].items():
 if rel not in plan['files']:assert sha(ROOT/rel)==expected,'Protected input changed: '+rel
obj='Assets/models/maps/spillway/spillway_cargo.obj'
old=Counter(S.read_obj(OUT/'before'/obj)[1]);new=Counter(S.read_obj(ROOT/obj)[1])
removed=Counter(S.read_obj(OUT/'removed.obj')[1]);added=Counter(S.read_obj(OUT/'added.obj')[1])
assert old-removed==new-added
doc='Assets/models/maps/spillway/spillway_cargo.vmdl';marker=b'_class = "PhysicsShapeList"'
b=(OUT/'before'/doc).read_bytes();a=(ROOT/doc).read_bytes()
assert b[b.index(marker):]==a[a.index(marker):]
compile((ROOT/'Tools/spillway_map.py').read_text(),'spillway_map.py','exec')
compile((ROOT/'Tools/spillway_service_cabinet.py').read_text(),'spillway_service_cabinet.py','exec')
report=dict(InstalledHashesMatch=True,OtherFacesPreserved=sum((old-removed).values()),RemovedTriangles=sum(removed.values()),
 AddedTriangles=sum(added.values()),PhysicsSuffixByteIdentical=True,CollisionSourcesUnchanged=True,SceneUnchanged=True,
 GeneratorSyntaxValid=True,CabinetBounds=plan['bounds'])
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
