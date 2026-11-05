from pathlib import Path
from collections import Counter
import hashlib,json,sys
import importlib.util
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/riverside/searchlight-v1'
sys.path.insert(0,str(ROOT/'Tools'))
import riverdale_splice as S,map_kit as K,riverside_parts as P,riverside_map as R
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
obj='Assets/models/maps/riverside/riverside_dressing.obj';doc='Assets/models/maps/riverside/riverside_dressing.vmdl'
before=Counter(S.read_obj(OUT/plan['baseline']/obj)[1]);after=Counter(S.read_obj(ROOT/obj)[1])
removed=Counter(S.read_obj(OUT/'removed.obj')[1]);added=Counter(S.read_obj(OUT/'added.obj')[1])
assert before-removed==after-added
lens=lambda f:Counter({k:v for k,v in f.items() if k[0]=='rs_lamp_search'})
assert lens(before)==lens(after) and sum(lens(after).values())==10
tx=lambda f:Counter({k:v for k,v in f.items() if k[0].startswith('tx_')})
assert tx(before)==tx(after) and sum(tx(after).values())==29568
b=(OUT/plan['baseline']/doc).read_bytes();a=(ROOT/doc).read_bytes();marker=b'_class = "PhysicsShapeList"'
assert b[b.index(marker):]==a[a.index(marker):]
for rel in ('Tools/riverside_parts.py','Tools/riverside_searchlight.py'):compile((ROOT/rel).read_text(),rel,'exec')
invalid=0;degenerate=0
for paint,corners in added.elements():
 p=np.array([list(map(float,c[0].split())) for c in corners]);n=np.array([list(map(float,c[2].split())) for c in corners]);uv=np.array([list(map(float,c[1].split())) for c in corners])
 if not (np.isfinite(p).all() and np.isfinite(n).all() and np.isfinite(uv).all()):invalid+=1
 if np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))<1e-7:degenerate+=1
assert invalid==degenerate==0,(invalid,degenerate)
# Check the retained generator hook directly, without rebuilding the map.
tower=K.Model();head=P.guard_tower(tower,R.TOWER[0],R.TOWER[1],aim=R.SEARCH_TARGET);R.configure(tower)
assert np.allclose(head,plan['head'],atol=1e-9)
spec=importlib.util.spec_from_file_location('original_riverside_parts',OUT/plan['baseline']/'Tools/riverside_parts.py')
original_parts=importlib.util.module_from_spec(spec);spec.loader.exec_module(original_parts)
original_tower=K.Model();original_parts.guard_tower(original_tower,R.TOWER[0],R.TOWER[1],aim=R.SEARCH_TARGET)
shapes=lambda model:json.dumps([model.boxes,model.hulls],default=lambda a:np.asarray(a).tolist())
assert shapes(original_tower)==shapes(tower),'Generator collision changed'
K.write_obj(OUT/'generator-tower.obj',tower,'riverside_dressing');towerfaces=Counter(S.read_obj(OUT/'generator-tower.obj')[1])
assert not towerfaces-after,'The installed generator differs from the public tower'
report=dict(InstalledHashesMatch=True,OtherFacesPreserved=sum((before-removed).values()),
 RemovedTriangles=sum(removed.values()),AddedTriangles=sum(added.values()),OriginalLensFacesPreserved=10,
 NewTransformerFacesPreserved=29568,PhysicsSuffixByteIdentical=True,BeamAndSceneUnchanged=True,
 GeneratorMatchesInstalledTower=True,GeneratorTowerCollisionBoxes=len(tower.boxes),InvalidFaces=invalid,DegenerateFaces=degenerate)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
