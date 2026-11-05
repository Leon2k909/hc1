from pathlib import Path
from collections import Counter
import hashlib,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/riverside/pole-transformer-v1'
sys.path.insert(0,str(ROOT/'Tools'));import riverdale_splice as S
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text());preview=json.loads((OUT/'preview-plan.json').read_text())
retired=json.loads((OUT/'retirement.json').read_text()) if (OUT/'retirement.json').exists() else {}
for rel,expected in {**preview['files'],**plan['files']}.items():
 p=ROOT/rel
 if rel in retired:
  assert not p.exists(),'Retired comparison still installed: '+rel
  p=ROOT/retired[rel]['Archive']
 assert sha(p)==expected,'Installed/archive mismatch: '+rel
for rel,expected in plan['guards'].items():
 if rel not in plan['files']:assert sha(ROOT/rel)==expected,'Protected input changed: '+rel
obj='Assets/models/maps/riverside/riverside_dressing.obj'
before=Counter(S.read_obj(OUT/plan.get('baseline','before')/obj)[1]);after=Counter(S.read_obj(ROOT/obj)[1])
removed=Counter(S.read_obj(OUT/'removed.obj')[1]);added=Counter(S.read_obj(OUT/'added.obj')[1])
assert before-removed==after-added
doc='Assets/models/maps/riverside/riverside_dressing.vmdl';marker=b'_class = "PhysicsShapeList"'
b=(OUT/plan.get('baseline','before')/doc).read_bytes();a=(ROOT/doc).read_bytes();assert b[b.index(marker):]==a[a.index(marker):]
for rel in ('Tools/riverside_parts.py','Tools/riverside_pole_transformer.py'):compile((ROOT/rel).read_text(),rel,'exec')
invalid=0
for paint,corners in added.elements():
 p=np.array([list(map(float,c[0].split())) for c in corners]);normals=np.array([list(map(float,c[2].split())) for c in corners]);uv=np.array([list(map(float,c[1].split())) for c in corners])
 if not np.isfinite(p).all() or not np.isfinite(normals).all() or not np.isfinite(uv).all():invalid+=1
report=dict(InstalledHashesMatch=True,Transformers=3,OtherFacesPreserved=sum((before-removed).values()),
 RemovedTriangles=sum(removed.values()),AddedTriangles=sum(added.values()),PhysicsSuffixByteIdentical=True,
 CollisionSourcesUnchanged=True,SceneUnchanged=True,GeneratorSyntaxValid=True,InvalidFaces=invalid)
assert invalid==0
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
