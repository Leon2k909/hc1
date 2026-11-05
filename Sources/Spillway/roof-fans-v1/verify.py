from pathlib import Path
from collections import Counter
import sys,json,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'review'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_splice as S
import fan as G
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text());preview=json.loads((OUT/'preview-plan.json').read_text());installed=(OUT/'installed.json').exists()
for rel,expected in plan['guards'].items():
 if not installed or rel not in plan['files']:assert sha(ROOT/rel)==expected,'Protected input changed: '+rel
if installed:
 for rel,expected in plan['files'].items():assert sha(ROOT/rel)==expected,'Installed input changed: '+rel
for rel,expected in preview['files'].items():assert sha(ROOT/rel)==expected,rel
report={}
for name in G.PLACEMENTS:
 base=f'Assets/models/maps/spillway/{name}'
 before=Counter(S.read_obj(OUT/plan['baseline']/(base+'.obj'))[1]);after=Counter(S.read_obj((ROOT if installed else OUT/'install-stage')/(base+'.obj'))[1])
 removed=Counter(S.read_obj(OUT/(name+'-removed.obj'))[1]);added=Counter(S.read_obj(OUT/(name+'-added.obj'))[1])
 assert before-removed==after-added
 a=(OUT/plan['baseline']/(base+'.vmdl')).read_bytes();b=((ROOT if installed else OUT/'install-stage')/(base+'.vmdl')).read_bytes();marker=b'_class = "PhysicsShapeList"'
 assert a[a.index(marker):]==b[b.index(marker):]
 for paint,corners in added.elements():
  p=np.array([list(map(float,c[0].split())) for c in corners]);norm=np.array([list(map(float,c[2].split())) for c in corners]);uv=np.array([list(map(float,c[1].split())) for c in corners])
  assert np.isfinite(p).all() and np.isfinite(norm).all() and np.isfinite(uv).all()
  assert np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))>1e-7,(paint,p)
  assert np.allclose(np.linalg.norm(norm,axis=1),1,atol=.002)
 report[name]=dict(Fans=len(G.PLACEMENTS[name]),Removed=sum(removed.values()),Added=sum(added.values()),OtherFacesPreserved=sum((before-removed).values()),PhysicsByteIdentical=True)
for radius in (42,43):
 m=G.build(K.Model(),radius=radius);assert not m.boxes and not m.hulls
 p=np.array([p for faces in m.polygons.values() for points,n in faces for p in points])
 assert np.all(p[:,:2].min(0)>=-radius-4.001) and np.all(p[:,:2].max(0)<=radius+4.001)
 assert p[:,2].min()>=0 and p[:,2].max()<14.81
compile((OUT/'install-stage/Tools/spillway_map.py').read_text(),'spillway_map.py','exec')
report.update(Installed=installed,OldAssetsRetained=True,InvalidTriangles=0,ExistingCurbsLouversSceneAndCollisionUnchanged=True,MaximumHeightInches=14.8)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
