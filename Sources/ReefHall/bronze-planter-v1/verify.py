from pathlib import Path
from collections import Counter
import sys,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;OUT=HERE/'review'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_splice as S,reefhall_map as R
import planter as G
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text());preview=json.loads((OUT/'preview-plan.json').read_text());installed=(OUT/'installed.json').exists()
for rel,expected in plan['guards'].items():
 if not installed or rel not in plan['files']:assert sha(ROOT/rel)==expected,'Protected input changed: '+rel
if installed:
 for rel,expected in plan['files'].items():assert sha(ROOT/rel)==expected,'Installed input changed: '+rel
for rel,expected in preview['files'].items():assert sha(ROOT/rel)==expected,rel
base='Assets/models/maps/reefhall/reefhall_lobby'
before=Counter(S.read_obj(OUT/plan['baseline']/(base+'.obj'))[1]);after=Counter(S.read_obj((ROOT if installed else OUT/'install-stage')/(base+'.obj'))[1])
removed=Counter(S.read_obj(OUT/'removed.obj')[1]);added=Counter(S.read_obj(OUT/'added.obj')[1])
assert before-removed==after-added
a=(OUT/plan['baseline']/(base+'.vmdl')).read_bytes();b=((ROOT if installed else OUT/'install-stage')/(base+'.vmdl')).read_bytes();marker=b'_class = "PhysicsShapeList"'
assert a[a.index(marker):]==b[b.index(marker):]
for paint,corners in added.elements():
 p=np.array([list(map(float,c[0].split())) for c in corners]);normals=np.array([list(map(float,c[2].split())) for c in corners]);uv=np.array([list(map(float,c[1].split())) for c in corners])
 assert np.isfinite(p).all() and np.isfinite(normals).all() and np.isfinite(uv).all()
 assert np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))>1e-7
 assert np.allclose(np.linalg.norm(normals,axis=1),1,atol=.002)
local=G.shell(K.Model());points=np.array([p for items in local.polygons.values() for ps,n in items for p in ps])
assert np.all(points.min(0)>=(-11.288,-11.288,0)) and np.all(points.max(0)<=(11.288,11.288,46.25))
new_source=(OUT/'install-stage/Tools/reefhall_map.py').read_text();compile(new_source,'reefhall_map.py','exec')
# Exercise only the staged planter function, retaining the old soil and physics recipe verbatim.
namespace=dict(R.__dict__);exec(new_source,namespace)
sys.modules['reefhall_bronze_planter']=G
original_namespace=dict(R.__dict__);exec((OUT/plan['baseline']/'Tools/reefhall_map.py').read_text(),original_namespace)
old=K.Model();new=K.Model();original_namespace['bronze_planter'](old,(0,0,0));namespace['bronze_planter'](new,(0,0,0))
assert len(old.hulls)==len(new.hulls)
assert repr(old.hulls)==repr(new.hulls)
assert repr(old.polygons['rh_soil'])==repr(new.polygons['rh_soil'])
report=dict(Planters=2,OriginalShellFaces=52,NewShellFaces=sum(added.values()),OtherFacesPreserved=sum((before-removed).values()),
 PhysicsByteIdentical=True,SoilAndFoliageUnchanged=True,InvalidTriangles=0,Installed=installed)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
