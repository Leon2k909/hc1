"""Compare the narrow vessel substitution without regenerating Riverside."""
from pathlib import Path
import sys,ast,collections,json
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/water-tank-v1';sys.path.insert(0,str(ROOT/'Tools'))
import riverside_parts as P
import riverside_map as R
import map_kit as K
tree=ast.parse((OUT/'install-before/riverside_parts.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='water_tower')
env=dict(P.__dict__);exec(compile(ast.Module(body=[fn],type_ignores=[]),'old-water-tower','exec'),env)
P.reset();old=K.Model();env['water_tower'](old,*R.WATER_TOWER);lights=list(P.LIGHTS)
P.reset();new=K.Model();P.water_tower(new,*R.WATER_TOWER,tank_model=True)
def faces(m):return collections.Counter((paint,tuple(tuple(round(float(q),6) for q in pt) for pt in pts)) for paint,polys in m.polygons.items() for pts,norm in polys)
a,b=faces(old),faces(new);assert not b-a
removed=a-b;triangles=sum((len(pts)-2)*count for (paint,pts),count in removed.items());assert triangles==224
assert str(old.boxes)==str(new.boxes) and str(old.hulls)==str(new.hulls) and lights==P.LIGHTS
assert len(P.WATER_TANKS)==1;position=K.to_world(P.WATER_TANKS[0][1]).tolist();assert position==[3600.,-1688.,1196.]
P.reset();control=K.Model();P.water_tower(control,*R.WATER_TOWER);assert faces(control)==a and not P.WATER_TANKS
result=dict(OnlyOriginalTankRemoved=True,RemovedTriangles=triangles,OriginalStructurePreserved=True,CollisionPreserved=True,PointLightsPreserved=True,DefaultTowerUnchanged=True,Position=position)
(OUT/'generator-check.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
