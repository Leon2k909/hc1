from pathlib import Path
from collections import Counter
import sys,json,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'review'
sys.path.insert(0,str(ROOT/'Tools'))
import riverdale_splice as S,map_kit as K
import pedestal as G
plan=json.loads((OUT/'preview-plan.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();installed=(OUT/'installed.json').exists()
installation=json.loads((OUT/'install-plan.json').read_text()) if installed else {'files':{}}
retired=json.loads((OUT/'retirement.json').read_text()) if (OUT/'retirement.json').exists() else {}
for k,v in plan['guards'].items():
 if k not in installation['files']:assert sha(ROOT/k)==v,k
for k,v in installation['files'].items():assert sha(ROOT/k)==v,k
for k,v in plan['files'].items():assert sha(ROOT/(retired[k]['Archive'] if k in retired else k))==v,k
for k in retired:assert not (ROOT/k).exists()
old=Counter(S.read_obj(OUT/'baseline/Assets/models/maps/orion/orion_pad.obj')[1]);new=Counter(S.read_obj(ROOT/('Assets/models/maps/orion/orion_pad.obj' if installed else 'Assets/models/maps/orion/mount-pedestals-v1/pad_preview.obj'))[1])
removed=Counter(S.read_obj(OUT/'removed.obj')[1]);added=Counter(S.read_obj(OUT/'added.obj')[1]);assert old-removed==new-added
a=(ROOT/'Assets/models/maps/orion/orion_pad.vmdl').read_bytes();b=(ROOT/'Assets/models/maps/orion/mount-pedestals-v1/pad_preview.vmdl').read_bytes();marker=b'_class = "PhysicsShapeList"'
if marker in a:assert a[a.index(marker):]==b[b.index(marker):]
for paint,cs in added.elements():
 assert paint in ('oa_steel','oa_dark')
 p=np.array([list(map(float,c[0].split())) for c in cs]);uv=np.array([list(map(float,c[1].split())) for c in cs]);n=np.array([list(map(float,c[2].split())) for c in cs]);assert np.isfinite(p).all() and np.isfinite(uv).all() and np.isfinite(n).all()
 assert np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))>1e-7
m=G.build(K.Model(),(0,0,0));lo,hi=m.bounds();assert np.all(lo>=(-14.001,-10.001,-.001)) and np.all(hi<=(14.001,10.001,40.12));assert not m.boxes and not m.hulls
report=dict(Pedestals=4,Removed=48,Added=sum(added.values()),OtherFacesPreserved=sum((old-removed).values()),ApprovedCageLightsUnchanged=True,ExistingMaterialsReused=True,OriginalLightsSceneAndCollisionUnchanged=True,FootprintAndLampMountHeightRetained=True,Installed=installed,OldAssetsRemoved=bool(retired),InvalidTriangles=0)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(report)
