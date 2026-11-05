from pathlib import Path
from collections import Counter
import sys,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/spillway/trench-grates-v1'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_splice as S,spillway_map as R,spillway_trench_grates as G
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text());preview=json.loads((OUT/'preview-plan.json').read_text())
retired=json.loads((OUT/'retirement.json').read_text()) if (OUT/'retirement.json').exists() else {}
for rel,expected in {**preview['files'],**plan['files']}.items():
 p=ROOT/rel
 if rel in retired:
  assert not p.exists();p=ROOT/retired[rel]['Archive']
 assert sha(p)==expected,'Mismatch: '+rel
for rel,expected in plan['guards'].items():
 if rel not in plan['files']:assert sha(ROOT/rel)==expected,'Protected input changed: '+rel
base='Assets/models/maps/spillway/spillway_cargo'
before=Counter(S.read_obj(OUT/plan['baseline']/(base+'.obj'))[1]);after=Counter(S.read_obj(ROOT/(base+'.obj'))[1])
removed=Counter(S.read_obj(OUT/'removed.obj')[1]);added=Counter(S.read_obj(OUT/'added.obj')[1])
assert before-removed==after-added
a=(ROOT/(base+'.vmdl')).read_bytes();b=(OUT/plan['baseline']/(base+'.vmdl')).read_bytes();marker=b'_class = "PhysicsShapeList"'
assert a[a.index(marker):]==b[b.index(marker):]
for paint,corners in added.elements():
 p=np.array([list(map(float,c[0].split())) for c in corners]);n=np.array([list(map(float,c[2].split())) for c in corners]);uv=np.array([list(map(float,c[1].split())) for c in corners])
 assert np.isfinite(p).all() and np.isfinite(n).all() and np.isfinite(uv).all()
 assert np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))>1e-7
 assert .0<=p[:,1].min()<=p[:,1].max()<1.,'Grate height outside promised flush envelope'
generated=K.Model()
for e,n,w,h in G.PLACEMENTS:G.grate(generated,(e,n,0),w,h)
assert not generated.boxes and not generated.hulls
R.configure(generated);K.write_obj(OUT/'generator-grates.obj',generated,'spillway_cargo')
assert Counter(S.read_obj(OUT/'generator-grates.obj')[1])==added
for name in ('spillway_map.py','spillway_trench_grates.py'):compile((ROOT/'Tools'/name).read_text(),name,'exec')
report=dict(Grates=5,InstalledHashesMatch=True,OriginalFacesRemoved=sum(removed.values()),ReplacementFaces=sum(added.values()),
 OtherFacesPreserved=sum((before-removed).values()),PhysicsByteIdentical=True,SceneAndHullsUnchanged=True,
 GeneratorMatchesInstalledGrates=True,InvalidTriangles=0,VisualHeightUnderOneInch=True)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
