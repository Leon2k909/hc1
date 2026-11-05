from pathlib import Path
from collections import Counter
import sys,json,hashlib,importlib.util
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/boxyard/pipe-stacks-v1'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_splice as S,boxyard_map as B,boxyard_pipe_stacks as G
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
base='Assets/models/maps/boxyard/boxyard_props'
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
for e,n,heading in G.PLACEMENTS:B.pipes(generated,e,n,heading)
B.configure(generated);K.write_obj(OUT/'generator-pipes.obj',generated,'boxyard_props')
assert Counter(S.read_obj(OUT/'generator-pipes.obj')[1])==added
spec=importlib.util.spec_from_file_location('boxyard_original',OUT/plan['baseline']/'Tools/boxyard_map.py');original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
old=K.Model()
for e,n,heading in G.PLACEMENTS:original.pipes(old,e,n,heading)
shapes=lambda m:json.dumps([m.boxes,m.hulls],default=lambda a:np.asarray(a).tolist())
assert shapes(old)==shapes(generated)
# Prove the original captured comparison still represents the old stack, not an installed replacement.
old_materials={f[0] for f in S.read_obj(ROOT/retired['Assets/models/maps/boxyard/pipe-stacks-v1/before.obj']['Archive'] if retired else ROOT/'Assets/models/maps/boxyard/pipe-stacks-v1/before.obj')[1]}
assert old_materials=={'bx_rust','bx_dark','rw_wood'}
for name in ('boxyard_map.py','boxyard_pipe_stacks.py'):compile((ROOT/'Tools'/name).read_text(),name,'exec')
report=dict(Stacks=2,HollowPipes=12,InstalledHashesMatch=True,OriginalFacesRemoved=sum(removed.values()),ReplacementFaces=sum(added.values()),
 OtherFacesPreserved=sum((before-removed).values()),PhysicsByteIdentical=True,SceneAndHullsUnchanged=True,
 GeneratorGeometryAndCollisionMatch=True,OldComparisonPreserved=True,InvalidTriangles=0)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
