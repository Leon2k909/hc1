"""Compare the narrow trailer change without regenerating map assets."""
from pathlib import Path
import sys,ast,collections,json
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/tv-aerial-v1'
sys.path.insert(0,str(ROOT/'Tools'))
import riverside_parts as P
import riverside_map as R
import map_kit as K
tree=ast.parse((OUT/'install-before/riverside_parts.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='trailer')
env=dict(P.__dict__);exec(compile(ast.Module(body=[fn],type_ignores=[]),'old-trailer','exec'),env)
args=(420,110,'rs_siding_teal');kwargs=dict(seed=12,door_side=-1,lit_share=.6,boarded_share=.15)
P.reset();old,oldinfo=env['trailer'](*args,**kwargs)
P.reset();new,newinfo=P.trailer(*args,**kwargs,aerial_model=True)
def faces(m):return collections.Counter((paint,tuple(tuple(round(float(q),6) for q in pt) for pt in pts)) for paint,polys in m.polygons.items() for pts,norm in polys)
a,b=faces(old),faces(new);assert not b-a and sum((a-b).values())==26
assert str(old.boxes)==str(new.boxes) and str(old.hulls)==str(new.hulls)
assert repr(oldinfo)==repr(newinfo)
assert len(P.AERIALS)==1
dst=K.Model();P.carry(dst,new,(-820,1050,0),0)
position=K.to_world(P.AERIALS[0][1]).tolist();assert all(abs(x-y)<1e-5 for x,y in zip(position,[1033.5,794.7722080465406,123]))
P.reset();control,_=P.trailer(*args,**kwargs);assert faces(control)==a and not P.AERIALS
result=dict(OnlyOriginalAerialRemoved=True,RemovedPolygons=26,CollisionPreserved=True,TrailerInfoAndRandomChoicesPreserved=True,DefaultTrailerUnchanged=True,Position=position)
(OUT/'generator-check.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
