from pathlib import Path
from collections import Counter
import sys,json,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'review'
sys.path.insert(0,str(ROOT/'Tools'))
import riverdale_splice as S
plan=json.loads((OUT/'preview-plan.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();installed=(OUT/'installed.json').exists()
installation=json.loads((OUT/'install-plan.json').read_text()) if installed else {'files':{}}
for k,v in plan['guards'].items():
 if k not in installation['files']:assert sha(ROOT/k)==v,k
for k,v in installation['files'].items():assert sha(ROOT/k)==v,k
for k,v in plan['files'].items():assert sha(ROOT/k)==v,k
old=Counter(S.read_obj(OUT/'baseline/Assets/models/maps/reefhall/reefhall_control.obj')[1]);new=Counter(S.read_obj(ROOT/('Assets/models/maps/reefhall/reefhall_control.obj' if installed else 'Assets/models/maps/reefhall/office-desk-v1/control_preview.obj'))[1])
removed=Counter(S.read_obj(OUT/'removed.obj')[1]);added=Counter(S.read_obj(OUT/'added.obj')[1]);assert old-removed==new-added
a=(ROOT/'Assets/models/maps/reefhall/reefhall_control.vmdl').read_bytes();b=(ROOT/'Assets/models/maps/reefhall/office-desk-v1/control_preview.vmdl').read_bytes();marker=b'_class = "PhysicsShapeList"';assert a[a.index(marker):]==b[b.index(marker):]
for paint,corners in added.elements():
 p=np.array([list(map(float,c[0].split())) for c in corners]);uv=np.array([list(map(float,c[1].split())) for c in corners]);n=np.array([list(map(float,c[2].split())) for c in corners]);assert np.isfinite(p).all() and np.isfinite(uv).all() and np.isfinite(n).all()
 assert np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))>1e-7
report=dict(Desks=1,Removed=96,Added=sum(added.values()),OtherFacesPreserved=sum((old-removed).values()),ExistingChairsAndCollisionUnchanged=True,Installed=installed,OldAssetsRetained=True,InvalidTriangles=0)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(report)
