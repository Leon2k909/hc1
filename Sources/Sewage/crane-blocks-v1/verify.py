from pathlib import Path
from collections import Counter
import sys,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/sewage/crane-blocks-v1'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_splice as S,sewage_map as R,sewage_crane_blocks as G
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text());preview=json.loads((OUT/'preview-plan.json').read_text())
for rel,expected in {**preview['files'],**plan['files']}.items():assert sha(ROOT/rel)==expected,'Mismatch: '+rel
for rel,expected in plan['guards'].items():
 if rel not in plan['files']:assert sha(ROOT/rel)==expected,'Protected input changed: '+rel
base='Assets/models/maps/sewage/sewage_details'
before=Counter(S.read_obj(OUT/plan['baseline']/(base+'.obj'))[1]);after=Counter(S.read_obj(ROOT/(base+'.obj'))[1])
removed=Counter(S.read_obj(OUT/'removed.obj')[1]);added=Counter(S.read_obj(OUT/'added.obj')[1])
assert before-removed==after-added
a=(ROOT/(base+'.vmdl')).read_bytes();b=(OUT/plan['baseline']/(base+'.vmdl')).read_bytes();marker=b'_class = "PhysicsShapeList"'
assert a[a.index(marker):]==b[b.index(marker):]
for paint,corners in added.elements():
 p=np.array([list(map(float,c[0].split())) for c in corners]);n=np.array([list(map(float,c[2].split())) for c in corners]);uv=np.array([list(map(float,c[1].split())) for c in corners])
 assert np.isfinite(p).all() and np.isfinite(n).all() and np.isfinite(uv).all()
 assert np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))>1e-7
generated=K.Model()
for centre in G.PLACEMENTS:G.block(generated,centre)
assert not generated.boxes and not generated.hulls
K.write_obj(OUT/'generator-blocks.obj',generated,'sewage_details')
assert Counter(S.read_obj(OUT/'generator-blocks.obj')[1])==added
R.PAINTS.update(steel=96,yellow=64);old=R.model()
for centre in G.PLACEMENTS:G.original(old,*centre)
assert not old.boxes and not old.hulls
for name in ('sewage_map.py','sewage_crane_blocks.py'):compile((ROOT/'Tools'/name).read_text(),name,'exec')
report=dict(Blocks=2,InstalledHashesMatch=True,OriginalFacesRemoved=sum(removed.values()),ReplacementFaces=sum(added.values()),
 OtherFacesPreserved=sum((before-removed).values()),ExistingChainsPreserved=True,PhysicsByteIdentical=True,SceneAndHullsUnchanged=True,
 GeneratorMatchesInstalledBlocks=True,OldAlternateRetained=True,InvalidTriangles=0)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
