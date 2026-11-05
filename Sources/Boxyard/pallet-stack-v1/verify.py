from pathlib import Path
from collections import Counter
import sys,json,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'review'
sys.path.insert(0,str(ROOT/'Tools'))
import riverdale_splice as S,map_kit as K
import stack as G
plan=json.loads((OUT/'preview-plan.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for k,v in plan['guards'].items():assert sha(ROOT/k)==v,k
for k,v in plan['files'].items():assert sha(OUT/'stage'/k)==v,k
imported=all((ROOT/k).exists() and sha(ROOT/k)==v for k,v in plan['files'].items())
preview_root=ROOT if imported else OUT/'stage'
old=Counter(S.read_obj(ROOT/'Assets/models/maps/boxyard/boxyard_props.obj')[1]);new=Counter(S.read_obj(preview_root/'Assets/models/maps/boxyard/pallet-stack-v1/props_preview.obj')[1])
removed=Counter(S.read_obj(OUT/'removed.obj')[1]);added=Counter(S.read_obj(OUT/'added.obj')[1]);assert old-removed==new-added
a=(ROOT/'Assets/models/maps/boxyard/boxyard_props.vmdl').read_bytes();b=(preview_root/'Assets/models/maps/boxyard/pallet-stack-v1/props_preview.vmdl').read_bytes();marker=b'_class = "PhysicsShapeList"';assert a[a.index(marker):]==b[b.index(marker):]
for paint,corners in added.elements():
 p=np.array([list(map(float,c[0].split())) for c in corners]);uv=np.array([list(map(float,c[1].split())) for c in corners]);n=np.array([list(map(float,c[2].split())) for c in corners]);assert np.isfinite(p).all() and np.isfinite(uv).all() and np.isfinite(n).all()
 assert np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))>1e-7
 assert np.allclose(np.linalg.norm(n,axis=1),1,atol=.002)
m=G.build(K.Model(),e=0,n=0);lo,hi=m.bounds();assert np.allclose(lo,(-23.62,-15.75,0),atol=.001) and np.allclose(hi,(23.62,15.75,17.01),atol=.001)
assert not m.boxes and not m.hulls
report=dict(Pallets=3,Removed=sum(removed.values()),Added=sum(added.values()),OtherFacesPreserved=sum((old-removed).values()),OriginalCollisionAndSceneUnchanged=True,OriginalEnvelopeRetained=True,PublicMapUnchanged=True,ApprovedPalletReused=True,Imported=imported,InvalidTriangles=0)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(report)
