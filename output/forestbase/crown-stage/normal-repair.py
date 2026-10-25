import sys,json,math,collections
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'Tools'))
from forestbase_crown_obj import read_faces,write_faces
out=Path('output/forestbase/crown-stage');folder=out/'models/maps/forestbase/fir';results=[]
for variant in 'abc':
 p=folder/f'fir_{variant}_distant.obj';write_faces(p,read_faces(p))
 for level in ('lod1','distant'):
  name=f'fir_{variant}_{level}.obj';before=read_faces(out/'normal-repair-before'/name);after=read_faces(folder/name);changed=0
  assert before.keys()==after.keys()
  for paint in before:
   geom=lambda rows:collections.Counter(tuple((v,t) for v,t,n in row) for row in rows)
   assert geom(before[paint])==geom(after[paint]),'Geometry/UV changed'
   if paint.endswith('_twig'):assert before[paint]==after[paint],'Needle normals changed'
   else:
    for a,b in zip(before[paint],after[paint]):
     for (v,t,n),(vv,tt,nn) in zip(a,b):
      assert (v,t)==(vv,tt)
      if n!=nn:
       assert sum(float(x)**2 for x in n.split())<1e-8
       assert abs(math.sqrt(sum(float(x)**2 for x in nn.split()))-1)<.0001
       changed+=1
  results.append(dict(file=name,changedOpaqueNormalCorners=changed,geometryUvsNeedleNormalsUnchanged=True))
(out/'normal-repair.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results))
