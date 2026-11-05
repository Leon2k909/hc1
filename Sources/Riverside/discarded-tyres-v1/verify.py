from pathlib import Path
from collections import Counter
import sys,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/riverside/discarded-tyres-v1'
sys.path.insert(0,str(ROOT/'Tools'));import riverdale_splice as S,map_kit as K,riverside_parts as P,riverside_map as R
import layout
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text());preview=json.loads((OUT/'preview-plan.json').read_text())
retired=json.loads((OUT/'retirement.json').read_text()) if (OUT/'retirement.json').exists() else {}
for rel,expected in {**preview['files'],**plan['files']}.items():
 p=ROOT/rel
 if rel in retired:
  assert not p.exists();p=ROOT/retired[rel]['Archive']
 assert sha(p)==expected,rel
for rel,expected in plan['guards'].items():
 if rel not in plan['files']:assert sha(ROOT/rel)==expected,rel
checks=[]
for group in plan['models']:
 name=group['asset'];base='Assets/models/maps/riverside/riverside_'+name
 before=Counter(S.read_obj(OUT/plan['baseline']/(base+'.obj'))[1]);after=Counter(S.read_obj(ROOT/(base+'.obj'))[1])
 removed=Counter(S.read_obj(OUT/(name+'-removed.obj'))[1]);added=Counter(S.read_obj(OUT/(name+'-added.obj'))[1])
 assert before-removed==after-added
 generated=K.Model()
 for group_name,centre in layout.placements():
  if group_name==name:P.tire(generated,centre,(0,0,1),r=12.5,w=8)
 R.configure(generated);K.write_obj(OUT/(name+'-generator.obj'),generated,'riverside_'+name)
 assert Counter(S.read_obj(OUT/(name+'-generator.obj'))[1])==added
 a=(ROOT/(base+'.vmdl')).read_bytes();b=(OUT/plan['baseline']/(base+'.vmdl')).read_bytes();marker=b'_class = "PhysicsShapeList"'
 assert a[a.index(marker):]==b[b.index(marker):]
 for paint,corners in added.elements():
  p=np.array([list(map(float,c[0].split())) for c in corners]);n=np.array([list(map(float,c[2].split())) for c in corners]);uv=np.array([list(map(float,c[1].split())) for c in corners])
  assert np.isfinite(p).all() and np.isfinite(n).all() and np.isfinite(uv).all()
  assert np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))>1e-7
 checks.append(dict(**group,OtherFacesExact=True,PhysicsByteIdentical=True,InvalidTriangles=0))
for name in ('riverside_parts.py','riverside_discarded_tyres.py'):compile((ROOT/'Tools'/name).read_text(),name,'exec')
report=dict(Models=checks,InstalledHashesMatch=True,SceneAndHullsUnchanged=True,GeneratorMatchesInstalledTyres=True)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
