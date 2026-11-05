from pathlib import Path
from collections import Counter
import sys,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/orion/yard-lamp-v1'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_splice as S,orion_map as R,orion_yard_lamp as G
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text());preview=json.loads((OUT/'preview-plan.json').read_text())
receipt=ROOT/'Sources/Orion/yard-lamp-v1/retirement/retirement.json'
retired=json.loads(receipt.read_text()) if receipt.exists() else {}
for rel,expected in {**preview['files'],**plan['files']}.items():
 p=ROOT/(retired[rel]['Archive'] if rel in retired else rel)
 assert sha(p)==expected,'Mismatch: '+rel
 if rel in retired:assert not (ROOT/rel).exists()
for rel,expected in plan['guards'].items():
 if rel not in plan['files']:assert sha(ROOT/rel)==expected,'Protected input changed: '+rel
base='Assets/models/maps/orion/orion_props'
before=Counter(S.read_obj(OUT/plan['baseline']/(base+'.obj'))[1]);after=Counter(S.read_obj(ROOT/(base+'.obj'))[1])
removed=Counter(S.read_obj(OUT/'removed.obj')[1]);added=Counter(S.read_obj(OUT/'added.obj')[1])
assert before-removed==after-added
a=(ROOT/(base+'.vmdl')).read_bytes();b=(OUT/plan['baseline']/(base+'.vmdl')).read_bytes();marker=b'_class = "PhysicsShapeList"'
assert a[a.index(marker):]==b[b.index(marker):]
for paint,corners in added.elements():
 p=np.array([list(map(float,c[0].split())) for c in corners]);n=np.array([list(map(float,c[2].split())) for c in corners]);uv=np.array([list(map(float,c[1].split())) for c in corners])
 assert np.isfinite(p).all() and np.isfinite(n).all() and np.isfinite(uv).all()
 assert np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))>1e-7
generated=G.head(K.Model());R.configure(generated)
assert not generated.boxes and not generated.hulls
generated_path=ROOT/'Sources/Orion/yard-lamp-v1/retirement/generator-head.obj'
K.write_obj(generated_path,generated,'orion_props');assert Counter(S.read_obj(generated_path)[1])==added
local=G.local();points=np.array([p for items in local.polygons.values() for ps,n in items for p in ps])
assert np.all(points.min(0)>=np.array((-5.001,-6.001,-4.201))) and np.all(points.max(0)<=np.array((5.001,6.001,4.001)))
old=(OUT/plan['baseline']/'Tools/orion_map.py').read_text();new=(ROOT/'Tools/orion_map.py').read_text()
lightline='    P.LIGHTS.append( ( "Yard post lamp", ( 181, 166, 84 ), OP.WARM, 420, False ) )'
assert lightline in old and lightline in new
for name in ('orion_map.py','orion_yard_lamp.py'):compile((ROOT/'Tools'/name).read_text(),name,'exec')
report=dict(Lamps=1,InstalledHashesMatch=True,OriginalFacesRemoved=sum(removed.values()),ReplacementFaces=sum(added.values()),
 OtherFacesPreserved=sum((before-removed).values()),ExistingPolePreserved=True,PointLightUnchanged=True,
 PhysicsByteIdentical=True,SceneAndHullsUnchanged=True,GeneratorMatchesInstalledHead=True,OldAlternateRemoved=bool(retired),InvalidTriangles=0)
(ROOT/'Sources/Orion/yard-lamp-v1/retirement/verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
